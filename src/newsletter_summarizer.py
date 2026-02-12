from __future__ import annotations

import re

from src.config import Settings
from src.models import EmailMessage, NewsletterSummary

NEWSLETTER_KEYWORDS = [
    "newsletter",
    "digest",
    "weekly",
    "daily update",
    "edition",
    "top stories",
    "highlights",
    "電子報",
    "週報",
    "最新內容",
    "精選",
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

PROMOTION_LABEL = "CATEGORY_PROMOTIONS"


def summarize_newsletters(messages: list[EmailMessage], settings: Settings) -> list[NewsletterSummary]:
    matched = [
        m
        for m in messages
        if _is_newsletter_source(m.sender, settings.newsletter_sources) or _looks_like_newsletter(m)
    ]
    summaries: list[NewsletterSummary] = []

    for msg in matched:
        text = f"{msg.subject}. {msg.snippet}. {msg.body_text}".strip()
        bullets = _extract_bullets(text, max_items=5)
        links = _extract_links(msg.body_text + " " + msg.snippet)

        summaries.append(
            NewsletterSummary(
                source=msg.sender,
                subject=msg.subject,
                bullets=bullets,
                links=links[:3],
            )
        )

    return summaries


def _is_newsletter_source(sender: str, sources: list[str]) -> bool:
    sender = sender.lower()
    for src in sources:
        rule = src.lower().strip()
        if not rule:
            continue
        if rule.startswith("@") and rule in sender:
            return True
        if rule in sender:
            return True
    return False


def _looks_like_newsletter(msg: EmailMessage) -> bool:
    full_text = f"{msg.sender} {msg.subject} {msg.snippet}".lower()
    if any(hint in full_text for hint in TRANSACTIONAL_HINTS):
        return False

    if any(keyword in full_text for keyword in NEWSLETTER_KEYWORDS):
        return True

    if PROMOTION_LABEL in set(msg.label_ids):
        sender_subject = f"{msg.sender} {msg.subject}".lower()
        promotion_hints = ["news", "digest", "update", "newsletter", "weekly", "daily", "電子報", "週報", "最新內容"]
        return any(hint in sender_subject for hint in promotion_hints)

    return False


def _extract_bullets(text: str, max_items: int = 5) -> list[str]:
    if not text:
        return ["(no content)"]

    pieces = re.split(r"[\n\.!?]", text)
    cleaned = [p.strip() for p in pieces if len(p.strip()) >= 20]
    if not cleaned:
        cleaned = [text.strip()[:120]]

    deduped: list[str] = []
    seen = set()
    for item in cleaned:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break

    return deduped


def _extract_links(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)]+", text)
