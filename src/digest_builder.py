from __future__ import annotations

from typing import Any


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
                lines.append(f"- {item['subject']} | {item['sender']} ({item['reason']})")
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

    if account_reports:
        lines.append("")
        for account in account_reports:
            name = account.get("display_name") or account.get("account_id", "unknown")
            important = len(account.get("important", []))
            moved = len(account.get("moved", []))
            spam = len(account.get("spam_suspects", []))
            newsletters = len(account.get("newsletters", []))
            lines.append(f"{name}")
            lines.append(f"重要信 {important} | 已搬移 {moved} | 垃圾疑似重要 {spam} | 電子報 {newsletters}")
            top_important = account.get("important", [])[:2]
            for item in top_important:
                lines.append(f"- {item['subject']}")
            lines.append("")

    if failed_accounts:
        lines.append("失敗帳號:")
        for failed in failed_accounts:
            lines.append(f"- {failed.get('account_id')}")

    return "\n".join(lines)[:4900]
