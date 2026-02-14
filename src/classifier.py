from __future__ import annotations

from dataclasses import dataclass, field, replace
import re

from src.config import Settings
from src.models import EmailMessage, MoveDecision


LOW_VALUE_PATTERNS = [
    r"weekly digest",
    r"newsletter",
    r"promotion",
    r"special offer",
    r"event reminder",
    r"you might like",
    r"limited time",
    r"exclusive deal",
    r"最新內容",
    r"精選",
]

NEWSLETTER_HINT_KEYWORDS = [
    "newsletter",
    "digest",
    "weekly",
    "daily update",
    "edition",
    "top stories",
    "highlights",
    "最新內容",
    "內容動態",
    "電子報",
    "週報",
    "精選",
]

NEWSLETTER_STRUCTURE_HINTS = [
    "unsubscribe",
    "manage preferences",
    "email preferences",
    "view in browser",
    "subscription",
    "取消訂閱",
    "退訂",
    "管理訂閱",
    "若您不想再收到",
]

TRANSACTIONAL_HINTS = [
    "receipt",
    "invoice",
    "verification",
    "security alert",
    "password reset",
    "billing",
    "付款",
    "帳單",
    "驗證碼",
]


@dataclass(slots=True, frozen=True)
class ScoringProfile:
    keep_threshold: int = 3
    move_threshold: int = -3
    newsletter_threshold: int = 3
    whitelist_sender_score: int = 8
    priority_keyword_score: int = 6
    high_interaction_sender_score: int = 2
    newsletter_source_penalty: int = 7
    newsletter_source_score: int = 6
    promotion_penalty: int = 4
    promotion_newsletter_score: int = 2
    social_penalty: int = 2
    social_newsletter_score: int = 1
    no_reply_penalty: int = 3
    low_value_penalty: int = 2
    low_value_newsletter_score: int = 1
    newsletter_hint_penalty: int = 1
    newsletter_hint_score: int = 2
    newsletter_structure_penalty: int = 1
    newsletter_structure_score: int = 3
    transactional_score: int = 3
    transactional_newsletter_penalty: int = 2
    list_unsubscribe_score: int = 8


@dataclass(slots=True)
class ScoreState:
    important: int = 0
    newsletter: int = 0
    keep_signals: list[str] = field(default_factory=list)
    move_signals: list[str] = field(default_factory=list)


class ClassificationResult:
    def __init__(self) -> None:
        self.important: list[dict] = []
        self.move_candidates: list[MoveDecision] = []
        self.newsletter_candidate_ids: set[str] = set()


def classify_messages(
    messages: list[EmailMessage],
    settings: Settings,
    high_interaction_senders: set[str] | None = None,
) -> ClassificationResult:
    high_interaction_senders = high_interaction_senders or set()
    interaction_bases = {_sender_base(sender.lower()) for sender in high_interaction_senders}
    scoring_profile = _resolve_scoring_profile(settings)
    result = ClassificationResult()

    for msg in messages:
        decision = _classify_single(msg, settings, interaction_bases, scoring_profile)
        if decision["action"] == "keep":
            result.important.append(
                {
                    "message_id": msg.id,
                    "subject": msg.subject,
                    "sender": msg.sender,
                    "snippet": msg.snippet,
                    "reason": decision["reason"],
                }
            )
        else:
            bucket = decision.get("bucket", "low_priority")
            result.move_candidates.append(
                MoveDecision(
                    message_id=msg.id,
                    subject=msg.subject,
                    sender=msg.sender,
                    reason=decision["reason"],
                    bucket=bucket,
                )
            )
            if bucket == "newsletter":
                result.newsletter_candidate_ids.add(msg.id)

    return result


def _classify_single(
    msg: EmailMessage,
    settings: Settings,
    high_interaction_senders: set[str],
    profile: ScoringProfile,
) -> dict[str, str]:
    sender_lower = msg.sender.lower()
    subject_lower = msg.subject.lower()
    snippet_lower = msg.snippet.lower()
    subject_snippet = f"{subject_lower} {snippet_lower}"

    if _match_sender(sender_lower, settings.exclude_important_senders):
        return {"action": "move", "reason": "manual exclude-important sender rule", "bucket": "low_priority"}

    if _contains_keywords(subject_snippet, settings.exclude_important_subject_keywords):
        return {"action": "move", "reason": "manual exclude-important subject rule", "bucket": "low_priority"}

    if _match_sender(sender_lower, settings.force_newsletter_senders):
        return {"action": "move", "reason": "manual newsletter sender rule", "bucket": "newsletter"}

    if _contains_keywords(subject_snippet, settings.force_newsletter_subject_keywords):
        return {"action": "move", "reason": "manual newsletter subject rule", "bucket": "newsletter"}

    score = _score_message(
        msg=msg,
        settings=settings,
        high_interaction_senders=high_interaction_senders,
        profile=profile,
    )
    return _decision_from_score(score, profile)


def _score_message(
    msg: EmailMessage,
    settings: Settings,
    high_interaction_senders: set[str],
    profile: ScoringProfile,
) -> ScoreState:
    state = ScoreState()
    sender_lower = msg.sender.lower()
    subject_snippet = f"{msg.subject.lower()} {msg.snippet.lower()}"
    full_text = f"{subject_snippet} {msg.body_text.lower()}"
    labels = set(msg.label_ids)

    if _match_sender(sender_lower, settings.whitelist_senders):
        state.important += profile.whitelist_sender_score
        state.keep_signals.append("whitelist sender")

    priority_hits = _keyword_hits(subject_snippet, settings.priority_keywords)
    if priority_hits:
        scored_hits = min(priority_hits, 2)
        state.important += scored_hits * profile.priority_keyword_score
        state.keep_signals.append(f"priority keywords x{priority_hits}")

    if _match_sender(sender_lower, settings.newsletter_sources):
        state.important -= profile.newsletter_source_penalty
        state.newsletter += profile.newsletter_source_score
        state.move_signals.append("newsletter source")

    if _sender_base(sender_lower) in high_interaction_senders:
        state.important += profile.high_interaction_sender_score
        state.keep_signals.append("high interaction sender")

    if "CATEGORY_PROMOTIONS" in labels:
        state.important -= profile.promotion_penalty
        state.newsletter = -100  # Force ignore: User requested to treat promotions as low priority, not newsletters
        state.move_signals.append("gmail promotions label")

    if "CATEGORY_SOCIAL" in labels:
        state.important -= profile.social_penalty
        state.newsletter = -100 # Force ignore: User requested to treat social as low priority, not newsletters
        state.move_signals.append("gmail social label")

    if "no-reply" in sender_lower or "noreply" in sender_lower:
        state.important -= profile.no_reply_penalty
        state.move_signals.append("no-reply sender")

    low_value_hits = _regex_hits(subject_snippet, LOW_VALUE_PATTERNS)
    if low_value_hits:
        hit_count = min(len(low_value_hits), 3)
        state.important -= hit_count * profile.low_value_penalty
        state.newsletter += min(len(low_value_hits), 2) * profile.low_value_newsletter_score
        state.move_signals.append(f"low-value hints x{len(low_value_hits)}")

    newsletter_hits = _keyword_hits(subject_snippet, NEWSLETTER_HINT_KEYWORDS)
    if newsletter_hits:
        hit_count = min(newsletter_hits, 3)
        state.important -= hit_count * profile.newsletter_hint_penalty
        state.newsletter += hit_count * profile.newsletter_hint_score
        state.move_signals.append(f"newsletter hints x{newsletter_hits}")

    structure_hits = _keyword_hits(full_text, NEWSLETTER_STRUCTURE_HINTS)
    if structure_hits:
        hit_count = min(structure_hits, 3)
        state.important -= hit_count * profile.newsletter_structure_penalty
        state.newsletter += hit_count * profile.newsletter_structure_score
        state.move_signals.append(f"newsletter structure hints x{structure_hits}")

    if msg.list_unsubscribe:
        state.important -= profile.newsletter_source_penalty
        state.newsletter += profile.list_unsubscribe_score
        state.move_signals.append("list-unsubscribe header found")

    transactional_hits = _keyword_hits(full_text, TRANSACTIONAL_HINTS)
    if transactional_hits:
        hit_count = min(transactional_hits, 2)
        state.important += hit_count * profile.transactional_score
        state.newsletter = max(0, state.newsletter - hit_count * profile.transactional_newsletter_penalty)
        state.keep_signals.append(f"transactional hints x{transactional_hits}")

    return state


def _decision_from_score(score: ScoreState, profile: ScoringProfile) -> dict[str, str]:
    if score.newsletter >= profile.newsletter_threshold and score.important < profile.keep_threshold:
        return {"action": "move", "reason": _format_score_reason("newsletter score", score), "bucket": "newsletter"}

    if score.important >= profile.keep_threshold:
        return {"action": "keep", "reason": _format_score_reason("important score", score), "bucket": "important"}

    if score.important <= profile.move_threshold:
        bucket = "newsletter" if score.newsletter >= max(1, profile.newsletter_threshold - 1) else "low_priority"
        return {"action": "move", "reason": _format_score_reason("low-priority score", score), "bucket": bucket}

    if score.newsletter >= max(1, profile.newsletter_threshold - 1) and score.newsletter > score.important:
        return {
            "action": "move",
            "reason": _format_score_reason("borderline newsletter score", score),
            "bucket": "newsletter",
        }

    return {"action": "keep", "reason": _format_score_reason("borderline keep score", score), "bucket": "important"}


def _format_score_reason(prefix: str, score: ScoreState) -> str:
    keep_part = ", ".join(score.keep_signals[:2]) if score.keep_signals else "none"
    move_part = ", ".join(score.move_signals[:2]) if score.move_signals else "none"
    return (
        f"{prefix} (important={score.important}, newsletter={score.newsletter}; "
        f"keep={keep_part}; move={move_part})"
    )


def _resolve_scoring_profile(settings: Settings) -> ScoringProfile:
    raw = settings.raw.get("scoring", {}) if isinstance(settings.raw, dict) else {}
    if not isinstance(raw, dict):
        raw = {}
    profile = ScoringProfile(
        keep_threshold=_safe_int(raw.get("keep_threshold"), 3),
        move_threshold=_safe_int(raw.get("move_threshold"), -3),
        newsletter_threshold=_safe_int(raw.get("newsletter_threshold"), 3),
        whitelist_sender_score=_safe_int(raw.get("whitelist_sender_score"), 8),
        priority_keyword_score=_safe_int(raw.get("priority_keyword_score"), 6),
        high_interaction_sender_score=_safe_int(raw.get("high_interaction_sender_score"), 2),
        newsletter_source_penalty=_safe_int(raw.get("newsletter_source_penalty"), 7),
        newsletter_source_score=_safe_int(raw.get("newsletter_source_score"), 6),
        promotion_penalty=_safe_int(raw.get("promotion_penalty"), 4),
        promotion_newsletter_score=_safe_int(raw.get("promotion_newsletter_score"), 2),
        social_penalty=_safe_int(raw.get("social_penalty"), 2),
        social_newsletter_score=_safe_int(raw.get("social_newsletter_score"), 1),
        no_reply_penalty=_safe_int(raw.get("no_reply_penalty"), 3),
        low_value_penalty=_safe_int(raw.get("low_value_penalty"), 2),
        low_value_newsletter_score=_safe_int(raw.get("low_value_newsletter_score"), 1),
        newsletter_hint_penalty=_safe_int(raw.get("newsletter_hint_penalty"), 1),
        newsletter_hint_score=_safe_int(raw.get("newsletter_hint_score"), 2),
        newsletter_structure_penalty=_safe_int(raw.get("newsletter_structure_penalty"), 1),
        newsletter_structure_score=_safe_int(raw.get("newsletter_structure_score"), 3),
        transactional_score=_safe_int(raw.get("transactional_score"), 3),
        transactional_newsletter_penalty=_safe_int(raw.get("transactional_newsletter_penalty"), 2),
        list_unsubscribe_score=_safe_int(raw.get("list_unsubscribe_score"), 8),
    )
    return _apply_move_mode(profile, settings.move_mode)


def _apply_move_mode(profile: ScoringProfile, move_mode: str) -> ScoringProfile:
    mode = move_mode.strip().lower()
    if mode == "conservative":
        return replace(
            profile,
            keep_threshold=profile.keep_threshold - 1,
            move_threshold=profile.move_threshold - 1,
            newsletter_threshold=profile.newsletter_threshold + 1,
        )
    if mode == "aggressive":
        return replace(
            profile,
            keep_threshold=profile.keep_threshold + 1,
            move_threshold=profile.move_threshold + 1,
            newsletter_threshold=max(1, profile.newsletter_threshold - 1),
        )
    return profile


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _keyword_hits(text: str, keywords: list[str]) -> int:
    text = text.lower()
    hits = 0
    for keyword in keywords:
        rule = keyword.lower().strip()
        if rule and rule in text:
            hits += 1
    return hits


def _regex_hits(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text):
            hits.append(pattern)
    return hits


def _contains_keywords(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def _match_sender(sender: str, whitelist: list[str]) -> bool:
    sender_email = _sender_base(sender).lower().strip()
    sender_domain = sender_email.split("@", 1)[1] if "@" in sender_email else ""

    for item in whitelist:
        rule = item.lower().strip()
        if not rule:
            continue
        if rule.startswith("@"):
            wanted_domain = rule[1:]
            if not wanted_domain:
                continue
            if sender_domain == wanted_domain or sender_domain.endswith(f".{wanted_domain}"):
                return True
            if rule in sender:
                return True
            continue
        if rule in sender_email:
            return True
        if rule in sender:
            return True
    return False


def _sender_base(sender: str) -> str:
    if "<" in sender and ">" in sender:
        return sender.split("<", 1)[1].rstrip(">")
    return sender
