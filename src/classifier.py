from __future__ import annotations

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
]


class ClassificationResult:
    def __init__(self) -> None:
        self.important: list[dict] = []
        self.move_candidates: list[MoveDecision] = []


def classify_messages(
    messages: list[EmailMessage],
    settings: Settings,
    high_interaction_senders: set[str] | None = None,
) -> ClassificationResult:
    high_interaction_senders = high_interaction_senders or set()
    result = ClassificationResult()

    for msg in messages:
        decision = _classify_single(msg, settings, high_interaction_senders)
        if decision["action"] == "keep":
            result.important.append(
                {
                    "message_id": msg.id,
                    "subject": msg.subject,
                    "sender": msg.sender,
                    "reason": decision["reason"],
                }
            )
        else:
            result.move_candidates.append(
                MoveDecision(
                    message_id=msg.id,
                    subject=msg.subject,
                    sender=msg.sender,
                    reason=decision["reason"],
                )
            )

    return result


def _classify_single(msg: EmailMessage, settings: Settings, high_interaction_senders: set[str]) -> dict[str, str]:
    sender_lower = msg.sender.lower()
    subject_lower = msg.subject.lower()
    snippet_lower = msg.snippet.lower()

    if _match_sender(sender_lower, settings.whitelist_senders):
        return {"action": "keep", "reason": "whitelist sender"}

    if _contains_keywords(subject_lower + " " + snippet_lower, settings.priority_keywords):
        return {"action": "keep", "reason": "priority keyword matched"}

    if _sender_base(sender_lower) in {s.lower() for s in high_interaction_senders}:
        return {"action": "keep", "reason": "high interaction sender"}

    labels = set(msg.label_ids)
    if "CATEGORY_PROMOTIONS" in labels or "CATEGORY_SOCIAL" in labels:
        return {"action": "move", "reason": "gmail category promotions/social"}

    if "no-reply" in sender_lower or "noreply" in sender_lower:
        if not _contains_keywords(subject_lower + " " + snippet_lower, settings.priority_keywords):
            return {"action": "move", "reason": "no-reply notification"}

    text = f"{subject_lower} {snippet_lower}"
    for pattern in LOW_VALUE_PATTERNS:
        if re.search(pattern, text):
            return {"action": "move", "reason": f"low-value pattern: {pattern}"}

    return {"action": "keep", "reason": "default keep in moderate mode"}


def _contains_keywords(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def _match_sender(sender: str, whitelist: list[str]) -> bool:
    for item in whitelist:
        rule = item.lower().strip()
        if not rule:
            continue
        if rule.startswith("@") and rule in sender:
            return True
        if rule in sender:
            return True
    return False


def _sender_base(sender: str) -> str:
    if "<" in sender and ">" in sender:
        return sender.split("<", 1)[1].rstrip(">")
    return sender
