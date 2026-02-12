from __future__ import annotations

from src.config import Settings
from src.models import EmailMessage, SpamFinding

IMPORTANT_HINTS = [
    "invoice",
    "payment",
    "billing",
    "驗證",
    "驗證碼",
    "帳單",
    "登入",
    "security",
    "deadline",
    "today",
    "面試",
    "客戶",
]

TIME_SENSITIVE_HINTS = ["today", "urgent", "deadline", "24 hours", "立即", "盡快"]


def inspect_spam_messages(
    spam_messages: list[EmailMessage],
    settings: Settings,
    trusted_senders: set[str] | None = None,
) -> list[SpamFinding]:
    trusted_senders = trusted_senders or set()
    findings: list[SpamFinding] = []

    for msg in spam_messages:
        score, reasons = _score_message(msg, settings, trusted_senders)
        if score >= 50:
            findings.append(
                SpamFinding(
                    message_id=msg.id,
                    subject=msg.subject,
                    sender=msg.sender,
                    score=score,
                    reasons=reasons,
                )
            )

    findings.sort(key=lambda x: x.score, reverse=True)
    return findings


def _score_message(msg: EmailMessage, settings: Settings, trusted_senders: set[str]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    sender = msg.sender.lower()
    combined_text = f"{msg.subject} {msg.snippet} {msg.body_text}".lower()

    if any(k.lower() in combined_text for k in settings.priority_keywords):
        score += 35
        reasons.append("priority keyword matched")

    keyword_hits = sum(1 for hint in IMPORTANT_HINTS if hint in combined_text)
    if keyword_hits:
        delta = min(30, keyword_hits * 6)
        score += delta
        reasons.append(f"important hints x{keyword_hits}")

    if any(h in combined_text for h in TIME_SENSITIVE_HINTS):
        score += 15
        reasons.append("time-sensitive wording")

    if _sender_base(sender) in {s.lower() for s in trusted_senders}:
        score += 20
        reasons.append("trusted sender history")

    if any(sender_rule.lower() in sender for sender_rule in settings.whitelist_senders):
        score += 20
        reasons.append("whitelist sender")

    return min(score, 100), reasons or ["no strong importance signal"]


def _sender_base(sender: str) -> str:
    if "<" in sender and ">" in sender:
        return sender.split("<", 1)[1].rstrip(">")
    return sender
