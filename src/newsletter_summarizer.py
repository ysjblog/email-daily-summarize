from __future__ import annotations

import re

from src.config import Settings
from src.models import EmailMessage, NewsletterSummary


def summarize_newsletters(messages: list[EmailMessage], settings: Settings) -> list[NewsletterSummary]:
    matched = [m for m in messages if _is_newsletter_source(m.sender, settings.newsletter_sources)]
    seen_sources: set[str] = set()
    summaries: list[NewsletterSummary] = []

    for msg in matched:
        sender_key = msg.sender.lower()
        if sender_key in seen_sources:
            continue
        seen_sources.add(sender_key)

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
