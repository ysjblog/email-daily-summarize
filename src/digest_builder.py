from __future__ import annotations

from typing import Any, Callable


LINE_MAX_CHARS = 4900
LINE_SECTION_LIMIT = 3
IMPORTANT_SNIPPET_MAX_CHARS = 20


def build_combined_digest(
    run_id: str,
    account_reports: list[dict[str, Any]],
    failed_accounts: list[dict[str, str]],
) -> str:
    lines: list[str] = [f"# Email Digest {run_id}", ""]

    if not account_reports:
        lines.append("- No successful account runs.")
        lines.append("")

    for account in account_reports:
        name = account.get("display_name") or account.get("account_id", "unknown")
        lines.append(f"## Account: {name} ({account.get('account_id', 'unknown')})")
        lines.append("")

        important = account.get("important", [])
        moved = account.get("moved", [])
        spam_findings = account.get("spam_suspects", [])
        newsletters = account.get("newsletters", [])

        lines.append("### 1) Important Emails")
        if important:
            for item in important[:10]:
                sender = item.get("sender", "unknown sender")
                subject = item.get("subject", "(no subject)")
                lines.append(f"- {sender} | {subject}")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("### 2) Moved Emails")
        if moved:
            for item in moved[:20]:
                lines.append(f"- {item['subject']} | {item['sender']} ({item['reason']})")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("### 3) Spam Possible Important Emails")
        if spam_findings:
            for finding in spam_findings:
                tier = "High" if finding.get("score", 0) >= 70 else "Review"
                reasons = ", ".join(finding.get("reasons", []))
                lines.append(
                    f"- [{tier}] {finding.get('subject', '')} | {finding.get('sender', '')} "
                    f"| score={finding.get('score', 0)} | {reasons}"
                )
        else:
            lines.append("- None")
        lines.append("")

        lines.append("### 4) Locked Newsletter Highlights")
        if newsletters:
            for summary in newsletters:
                lines.append(f"- {summary.get('subject', '')} ({summary.get('source', '')})")
                for bullet in summary.get("bullets", [])[:5]:
                    lines.append(f"  - {bullet}")
        else:
            lines.append("- None")
        lines.append("")

    lines.append("## Failed Accounts")
    if failed_accounts:
        for failed in failed_accounts:
            lines.append(f"- {failed.get('account_id')}: {failed.get('error')}")
    else:
        lines.append("- None")

    return "\n".join(lines)


def build_line_digest(run_id: str, account_reports: list[dict[str, Any]], failed_accounts: list[dict[str, str]]) -> str:
    lines = [f"[Email Digest] {run_id}"]

    if not account_reports:
        lines.extend(["", "無成功帳號。"])
    else:
        lines.append("")
        for account in account_reports:
            name = account.get("display_name") or account.get("account_id", "unknown")
            important = account.get("important", [])
            moved = account.get("moved", [])
            spam_suspects = account.get("spam_suspects", [])
            newsletters = account.get("newsletters", [])

            lines.append(f"【{name}】")
            lines.extend(
                _render_line_section(
                    title="1) 重要信件主旨",
                    items=important,
                    renderer=_render_important_item,
                    max_items=None,
                )
            )
            lines.extend(
                _render_line_section(
                    title="2) 已搬移摘要",
                    items=moved,
                    renderer=lambda item: [
                        f"- {item.get('sender', 'unknown sender')} | {item.get('subject', '(no subject)')}"
                    ],
                )
            )
            lines.extend(
                _render_line_section(
                    title="3) 疑似垃圾但重要",
                    items=spam_suspects,
                    renderer=lambda item: [
                        f"- {item.get('sender', 'unknown sender')} | {item.get('subject', '(no subject)')}"
                    ],
                )
            )
            lines.extend(
                _render_line_section(
                    title="4) 電子報摘要",
                    items=newsletters,
                    renderer=_render_newsletter_item,
                )
            )

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


def build_external_safe_digest(
    run_id: str,
    account_reports: list[dict[str, Any]],
    failed_accounts: list[dict[str, str]],
) -> str:
    lines = [f"[Email Digest Safe Summary] {run_id}", ""]
    if not account_reports:
        lines.append("- 無成功帳號。")
    else:
        for account in account_reports:
            name = account.get("display_name") or account.get("account_id", "unknown")
            lines.append(f"【{name}】")
            lines.append(f"- 重要信件數: {len(account.get('important', []))}")
            lines.append(f"- 已搬移數: {len(account.get('moved', []))}")
            lines.append(f"- 可疑垃圾郵件數: {len(account.get('spam_suspects', []))}")
            lines.append(f"- 電子報摘要數: {len(account.get('newsletters', []))}")
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


def _render_newsletter_item(item: dict[str, Any]) -> list[str]:
    subject = item.get("subject", "(no subject)")
    source = item.get("source", "unknown source")
    return [f"- {source} | {subject}"]


def _render_important_item(item: dict[str, Any]) -> list[str]:
    sender = item.get("sender", "unknown sender")
    subject = item.get("subject", "(no subject)")
    snippet = _truncate_text(str(item.get("snippet", "")).strip(), IMPORTANT_SNIPPET_MAX_CHARS)
    if snippet:
        return [f"- {sender} | {subject}", f"  摘要: {snippet}"]
    return [f"- {sender} | {subject}", "  摘要: (無)"]


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
