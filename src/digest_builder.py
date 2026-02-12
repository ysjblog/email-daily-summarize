from __future__ import annotations

from typing import Any, Callable


LINE_MAX_CHARS = 4900
LINE_SECTION_LIMIT = 3
IMPORTANT_SNIPPET_MAX_CHARS = 20
NEWSLETTER_SUMMARY_MAX_CHARS = 35


def build_combined_digest(
    run_id: str,
    account_reports: list[dict[str, Any]],
    failed_accounts: list[dict[str, str]],
) -> str:
    lines: list[str] = [f"# **Email Digest** `{run_id}`", ""]

    if not account_reports:
        lines.append("- _No successful account runs._")
        lines.append("")
    else:
        section_defs = [
            ("重要信件", "important", _render_markdown_important_item, 10),
            ("電子報摘要", "newsletters", _render_markdown_newsletter_item, 10),
            ("已搬移信件", "moved", _render_markdown_moved_item, 20),
            ("疑似垃圾但重要", "spam_suspects", _render_markdown_spam_item, 20),
        ]

        for index, (title, key, renderer, limit) in enumerate(section_defs, start=1):
            total = sum(len(account.get(key, [])) for account in account_reports)
            lines.append(f"## {index}) {_section_title_icon(key)} **{title}** _({total})_")
            lines.append("")

            for account in account_reports:
                lines.extend(
                    _render_markdown_account_section(
                        account=account,
                        key=key,
                        renderer=renderer,
                        max_items=limit,
                    )
                )
            lines.append("---")
            lines.append("")

    lines.append("## **Failed Accounts**")
    if failed_accounts:
        for failed in failed_accounts:
            lines.append(f"- **{failed.get('account_id')}**: _{failed.get('error')}_")
    else:
        lines.append("- _None_")

    return "\n".join(lines)


def build_line_digest(run_id: str, account_reports: list[dict[str, Any]], failed_accounts: list[dict[str, str]]) -> str:
    lines = [f"[Email Digest] {run_id}"]

    if not account_reports:
        lines.extend(["", "無成功帳號。"])
    else:
        lines.append("")
        section_defs = [
            ("重要信件", "important", _render_important_item, None),
            ("電子報摘要", "newsletters", _render_newsletter_item, LINE_SECTION_LIMIT),
            ("已搬移摘要", "moved", _render_line_moved_item, LINE_SECTION_LIMIT),
            ("疑似垃圾但重要", "spam_suspects", _render_line_spam_item, LINE_SECTION_LIMIT),
        ]

        for index, (title, key, renderer, max_items) in enumerate(section_defs, start=1):
            lines.append(f"【{index}) {_section_title_icon(key)} {title}】")
            for account in account_reports:
                lines.extend(
                    _render_line_account_section(
                        account=account,
                        key=key,
                        renderer=renderer,
                        max_items=max_items,
                    )
                )
            lines.append("")

    if failed_accounts:
        lines.append("失敗帳號:")
        for failed in failed_accounts:
            account_id = failed.get("account_id", "unknown")
            error = failed.get("error")
            if error:
                lines.append(f"- {account_id}: {error}")
            else:
                lines.append(f"- {account_id}")

    digest = "\n".join(lines).strip()
    return _truncate_line_digest(digest, LINE_MAX_CHARS)


def _render_markdown_account_section(
    account: dict[str, Any],
    key: str,
    renderer: Callable[[dict[str, Any]], list[str]],
    max_items: int,
) -> list[str]:
    name = account.get("display_name") or account.get("account_id", "unknown")
    account_id = account.get("account_id", "unknown")
    items = account.get(key, [])
    shown = items[:max_items]
    account_icon = _account_icon(account_id)

    lines = [f"### {account_icon} **{name}** (`{account_id}`) · _{len(items)} 封_"]
    lines.append("")
    if not shown:
        lines.append("- _📭 無_")
        lines.append("")
        return lines

    for idx, item in enumerate(shown):
        lines.extend(renderer(item))
        if idx < len(shown) - 1:
            lines.append("")
            lines.append("---")
            lines.append("")

    remaining = len(items) - len(shown)
    if remaining > 0:
        lines.append("")
        lines.append(f"- _...還有 {remaining} 筆_")

    lines.append("")
    return lines


def _render_markdown_important_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    snippet = _truncate_text(str(item.get("snippet", "")).strip(), 120)
    rendered_snippet = snippet if snippet else "(無)"
    return [
        f"- 👤 **寄件人**：`{sender}`",
        f"- ✉️ **主旨**：**{subject}**",
        f"- 📝 **摘要**：_{rendered_snippet}_",
    ]


def _render_markdown_newsletter_item(item: dict[str, Any]) -> list[str]:
    source = item.get("source", "unknown source")
    subject = item.get("subject", "(no subject)")
    bullets = item.get("bullets", [])
    summary = _truncate_text(str(bullets[0]).strip(), 120) if bullets else "(無摘要)"
    return [
        f"- 👤 **寄件人**：`{source}`",
        f"- ✉️ **主旨**：**{subject}**",
        f"- 📰 **摘要**：_{summary}_",
    ]


def _render_markdown_moved_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    reason = item.get("reason", "")
    return [
        f"- 👤 **寄件人**：`{sender}`",
        f"- 🔻 **主旨**：~~{subject}~~",
        f"- 🔴 **原因**：_{reason or '(無)'}_",
    ]


def _render_markdown_spam_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    score = item.get("score", 0)
    reasons = ", ".join(item.get("reasons", []))
    return [
        f"- 👤 **寄件人**：`{sender}`",
        f"- ⚠️ **主旨**：**{subject}**",
        f"- 🔴 **分數**：**{score}**",
        f"- 🧾 **原因**：_{reasons or '(無)'}_",
    ]


def build_external_safe_digest(
    run_id: str,
    account_reports: list[dict[str, Any]],
    failed_accounts: list[dict[str, str]],
) -> str:
    lines = [f"[Email Digest Safe Summary] {run_id}", ""]
    if not account_reports:
        lines.append("- 無成功帳號。")
    else:
        section_defs = [
            ("重要信件", "important"),
            ("電子報摘要", "newsletters"),
            ("已搬移信件", "moved"),
            ("疑似垃圾但重要", "spam_suspects"),
        ]

        for index, (title, key) in enumerate(section_defs, start=1):
            total = sum(len(account.get(key, [])) for account in account_reports)
            lines.append(f"【{index}) {_section_title_icon(key)} {title}】")
            lines.append(f"- 總數: {total}")
            for account in account_reports:
                name = account.get("display_name") or account.get("account_id", "unknown")
                account_id = account.get("account_id", "unknown")
                lines.append(f"- {_account_icon(account_id)} {name} ({account_id}): {len(account.get(key, []))}")
            lines.append("")

    if failed_accounts:
        lines.append("失敗帳號:")
        for failed in failed_accounts:
            account_id = failed.get("account_id", "unknown")
            lines.append(f"- {account_id}")

    return "\n".join(lines).strip()


def _render_line_section(
    title: str,
    items: list[dict[str, Any]],
    renderer: Callable[[dict[str, Any]], list[str]],
    max_items: int | None = LINE_SECTION_LIMIT,
) -> list[str]:
    shown = len(items) if max_items is None else min(len(items), max_items)
    lines = [f"{title} ({shown}/{len(items)})"]
    if not items:
        lines.extend(["- 無", ""])
        return lines

    sliced = items if max_items is None else items[:max_items]
    for item in sliced:
        lines.extend(renderer(item))

    remaining = len(items) - shown
    if remaining > 0:
        lines.append(f"- ...還有 {remaining} 筆")

    lines.append("")
    return lines


def _render_line_account_section(
    account: dict[str, Any],
    key: str,
    renderer: Callable[[dict[str, Any]], list[str]],
    max_items: int | None,
) -> list[str]:
    name = account.get("display_name") or account.get("account_id", "unknown")
    account_id = account.get("account_id", "unknown")
    items = account.get(key, [])
    shown = len(items) if max_items is None else min(len(items), max_items)
    sliced = items if max_items is None else items[:max_items]
    account_icon = _account_icon(account_id)

    lines = [f"＜{account_icon} {name} ({account_id})＞ ({shown}/{len(items)})"]
    if not items:
        lines.extend(["- 📭 無", ""])
        return lines

    for item in sliced:
        lines.extend(renderer(item))

    remaining = len(items) - shown
    if remaining > 0:
        lines.append(f"- ...還有 {remaining} 筆")

    lines.append("")
    return lines


def _render_newsletter_item(item: dict[str, Any]) -> list[str]:
    subject = item.get("subject", "(no subject)")
    source = item.get("source", "unknown source")
    bullets = item.get("bullets", [])
    summary = _truncate_text(str(bullets[0]).strip(), NEWSLETTER_SUMMARY_MAX_CHARS) if bullets else "(無)"
    return [f"- 👤 寄件人: {source}", f"  ✉️ 主旨: {subject}", f"  📰 摘要: {summary}"]


def _render_important_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    snippet = _truncate_text(str(item.get("snippet", "")).strip(), IMPORTANT_SNIPPET_MAX_CHARS)
    if snippet:
        return [f"- 👤 寄件人: {sender}", f"  ✉️ 主旨: {subject}", f"  📝 摘要: {snippet}"]
    return [f"- 👤 寄件人: {sender}", f"  ✉️ 主旨: {subject}", "  📝 摘要: (無)"]


def _render_line_moved_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    reason = str(item.get("reason", "")).strip()
    rendered_reason = _truncate_text(reason, NEWSLETTER_SUMMARY_MAX_CHARS) if reason else "(無)"
    return [f"- 👤 寄件人: {sender}", f"  🔻 主旨: ~~{subject}~~", f"  🔴 原因: {rendered_reason}"]


def _render_line_spam_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    score = item.get("score", 0)
    return [f"- 👤 寄件人: {sender}", f"  ⚠️ 主旨: {subject}", f"  🔴 分數: {score}"]


def _account_icon(account_id: object) -> str:
    account_key = str(account_id).strip().lower()
    if account_key == "work":
        return "💼"
    if account_key == "personal":
        return "🏠"
    return "📫"


def _section_title_icon(key: str) -> str:
    mapping = {
        "important": "⭐",
        "newsletters": "📰",
        "moved": "📦",
        "spam_suspects": "🚨",
    }
    return mapping.get(key, "📌")


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[: max_chars - 3]}..."


def _truncate_line_digest(digest: str, max_chars: int) -> str:
    if len(digest) <= max_chars:
        return digest

    suffix = "\n\n[訊息過長，已截斷]"
    available = max_chars - len(suffix)
    if available <= 0:
        return digest[:max_chars]
    return f"{digest[:available].rstrip()}{suffix}"
