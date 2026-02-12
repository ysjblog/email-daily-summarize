from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.auth.google_oauth import obtain_refresh_token, read_client_credentials, save_refresh_token
from src.classifier import classify_messages
from src.config import AccountSettings, ConfigError, Settings, load_settings
from src.digest_builder import build_combined_digest, build_line_digest
from src.env_utils import load_env_into_os
from src.gmail_client import GmailClient
from src.logging_utils import build_logger
from src.models import RunReport, utc_now_iso
from src.newsletter_summarizer import summarize_newsletters
from src.notifiers.gmail_notifier import GmailNotifier
from src.notifiers.line_notifier import LineNotifier
from src.notifiers.slack_bot_notifier import SlackBotNotifier
from src.spam_inspector import inspect_spam_messages
from src.state_store import StateStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily Gmail summarize automation")
    parser.add_argument("--config", default="config/settings.yaml", help="path to settings yaml")
    parser.add_argument("--env-file", default=".env", help="path to .env file")

    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run pipeline with move actions")
    run.add_argument("--account", help="run only one account id", default=None)

    dry_run = sub.add_parser("dry-run", help="run pipeline without moving emails")
    dry_run.add_argument("--account", help="run only one account id", default=None)

    backfill = sub.add_parser("backfill", help="run historical dry-run")
    backfill.add_argument("--days", type=int, default=7, help="how many days to backfill")
    backfill.add_argument("--account", help="run only one account id", default=None)

    auth = sub.add_parser("auth", help="authentication related commands")
    auth_sub = auth.add_subparsers(dest="auth_cmd", required=True)

    login = auth_sub.add_parser("login", help="interactive Google OAuth login for an account")
    login.add_argument("--account", required=True, help="account id from settings.yaml")
    login.add_argument("--email", required=False, help="Google login hint email")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_into_os(args.env_file, override=False)
    settings = load_settings(args.config)
    logger = build_logger()

    if args.cmd == "auth":
        if args.auth_cmd == "login":
            return auth_login(settings, args.account, args.email, args.env_file)
        return 1

    if args.cmd == "run":
        run_all_accounts(settings, dry_run=False, target_account=args.account, logger_name=logger.name)
        return 0

    if args.cmd == "dry-run":
        run_all_accounts(settings, dry_run=True, target_account=args.account, logger_name=logger.name)
        return 0

    if args.cmd == "backfill":
        tz = ZoneInfo(settings.timezone)
        for day_offset in range(args.days, 0, -1):
            end_dt = datetime.now(tz=tz) - timedelta(days=day_offset - 1)
            start_dt = end_dt - timedelta(days=1)
            run_all_accounts(
                settings,
                dry_run=True,
                target_account=args.account,
                window_start=start_dt,
                window_end=end_dt,
                logger_name=logger.name,
            )
        return 0

    return 1


def auth_login(settings: Settings, account_id: str, email: str | None, env_path: str) -> int:
    account = settings.find_account(account_id)
    client_id, client_secret = read_client_credentials(account.env_prefix)
    refresh_token = obtain_refresh_token(client_id=client_id, client_secret=client_secret, login_hint=email)
    key = save_refresh_token(env_path, account.env_prefix, refresh_token)
    print(f"Saved refresh token for account={account.id} into {key}")
    return 0


def run_all_accounts(
    settings: Settings,
    dry_run: bool,
    target_account: str | None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    logger_name: str = "daily-summarize",
) -> dict[str, Any]:
    logger = build_logger(logger_name)
    run_id = datetime.now(tz=ZoneInfo(settings.timezone)).strftime("%Y-%m-%d-%H%M")

    accounts = select_accounts(settings, target_account)
    account_reports: list[RunReport] = []
    failed_accounts: list[dict[str, str]] = []
    sender_clients: list[GmailClient] = []

    for account in accounts:
        account_cfg = settings.for_account(account)
        try:
            report, sender_client = execute_account(
                settings=account_cfg,
                account=account,
                dry_run=dry_run,
                run_id=run_id,
                window_start=window_start,
                window_end=window_end,
                logger_name=logger_name,
            )
            account_reports.append(report)
            sender_clients.append(sender_client)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("account pipeline failed: %s", account.id)
            failed_accounts.append({"account_id": account.id, "error": str(exc)})
            failure_report = build_failure_report(
                run_id=run_id,
                account=account,
                dry_run=dry_run,
                window_start=window_start,
                window_end=window_end,
                error=str(exc),
                timezone=settings.timezone,
            )
            write_account_reports(failure_report, "")

    combined_digest = build_combined_digest(
        run_id=run_id,
        account_reports=[r.to_dict() for r in account_reports],
        failed_accounts=failed_accounts,
    )
    write_combined_reports(run_id, dry_run, account_reports, failed_accounts, combined_digest)

    deliver_digest(
        settings=settings,
        digest=combined_digest,
        line_digest=build_line_digest(run_id, [r.to_dict() for r in account_reports], failed_accounts),
        run_id=run_id,
        logger=logger,
        sender_client=sender_clients[0] if sender_clients else None,
    )

    return {
        "run_id": run_id,
        "success": [r.account_id for r in account_reports],
        "failed": failed_accounts,
    }


def select_accounts(settings: Settings, target_account: str | None) -> list[AccountSettings]:
    if target_account:
        account = settings.find_account(target_account)
        if not account.enabled:
            raise ConfigError(f"Account is disabled: {target_account}")
        return [account]
    return settings.enabled_accounts()


def execute_account(
    settings: Settings,
    account: AccountSettings,
    dry_run: bool,
    run_id: str,
    window_start: datetime | None,
    window_end: datetime | None,
    logger_name: str,
) -> tuple[RunReport, GmailClient]:
    logger = build_logger(logger_name)
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz=tz)

    gmail = GmailClient.from_env_prefix(account.env_prefix)
    state_store = StateStore(account_id=account.id)
    state = state_store.load()

    end_dt = window_end or now
    if window_start is not None:
        start_dt = window_start
    elif state.last_successful_run:
        start_dt = datetime.fromisoformat(state.last_successful_run.replace("Z", "+00:00")).astimezone(tz)
    else:
        start_dt = end_dt - timedelta(hours=12)

    report = RunReport(
        run_id=run_id,
        mode="dry-run" if dry_run else "run",
        started_at=utc_now_iso(),
        finished_at="",
        window_start=start_dt.isoformat(),
        window_end=end_dt.isoformat(),
        account_id=account.id,
        display_name=account.display_name,
    )

    inbox_messages = fetch_messages(gmail, start_dt, end_dt, label_filter=["INBOX"])
    spam_messages = fetch_messages(gmail, end_dt - timedelta(hours=24), end_dt, label_filter=["SPAM"])

    interaction_senders = infer_high_interaction_senders(inbox_messages)
    classified = classify_messages(inbox_messages, settings, high_interaction_senders=interaction_senders)
    report.important = classified.important

    archive_label_id = gmail.get_or_create_label_id(settings.archive_label)

    moved_rows: list[dict] = []
    for decision in classified.move_candidates:
        row = {
            "message_id": decision.message_id,
            "subject": decision.subject,
            "sender": decision.sender,
            "reason": decision.reason,
        }
        moved_rows.append(row)
        if not dry_run:
            gmail.modify_labels(
                decision.message_id,
                add_label_ids=[archive_label_id],
                remove_label_ids=["INBOX"],
            )

    report.moved = moved_rows

    spam_findings = []
    if settings.spam_scan.get("enabled", True):
        spam_findings = inspect_spam_messages(spam_messages, settings, trusted_senders=interaction_senders)
    report.spam_suspects = [asdict(item) for item in spam_findings]

    newsletters = summarize_newsletters(inbox_messages, settings)
    report.newsletters = [asdict(item) for item in newsletters]

    report.finished_at = utc_now_iso()

    state.last_successful_run = utc_now_iso()
    state.processed_message_ids.extend([row["message_id"] for row in moved_rows])
    state_store.save(state)

    per_account_digest = build_combined_digest(
        run_id=run_id,
        account_reports=[report.to_dict()],
        failed_accounts=[],
    )
    write_account_reports(report, per_account_digest)

    logger.info("account completed: %s moved=%s important=%s", account.id, len(report.moved), len(report.important))
    return report, gmail


def build_failure_report(
    run_id: str,
    account: AccountSettings,
    dry_run: bool,
    window_start: datetime | None,
    window_end: datetime | None,
    error: str,
    timezone: str,
) -> RunReport:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz=tz)
    start_dt = window_start or (now - timedelta(hours=12))
    end_dt = window_end or now

    return RunReport(
        run_id=run_id,
        mode="dry-run" if dry_run else "run",
        started_at=utc_now_iso(),
        finished_at=utc_now_iso(),
        window_start=start_dt.isoformat(),
        window_end=end_dt.isoformat(),
        account_id=account.id,
        display_name=account.display_name,
        errors=[error],
    )


def fetch_messages(gmail: GmailClient, start: datetime, end: datetime, label_filter: list[str]) -> list:
    q = f"after:{int(start.timestamp())} before:{int(end.timestamp())}"
    refs = gmail.list_messages(query=q, label_ids=label_filter, max_results=300)
    return [gmail.get_message(ref["id"]) for ref in refs]


def infer_high_interaction_senders(messages: list) -> set[str]:
    senders: dict[str, int] = {}
    for msg in messages:
        sender = msg.sender.lower()
        senders[sender] = senders.get(sender, 0) + 1
    return {sender for sender, count in senders.items() if count >= 2}


def write_account_reports(report: RunReport, digest_markdown: str) -> None:
    report_dir = Path("data/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    base = f"{report.run_id}__{report.account_id}"
    json_path = report_dir / f"{base}.json"
    md_path = report_dir / f"{base}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

    with md_path.open("w", encoding="utf-8") as f:
        f.write(digest_markdown or "")


def write_combined_reports(
    run_id: str,
    dry_run: bool,
    account_reports: list[RunReport],
    failed_accounts: list[dict[str, str]],
    digest_markdown: str,
) -> None:
    report_dir = Path("data/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "mode": "dry-run" if dry_run else "run",
        "accounts": [r.to_dict() for r in account_reports],
        "failed_accounts": failed_accounts,
    }

    json_path = report_dir / f"{run_id}.json"
    md_path = report_dir / f"{run_id}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with md_path.open("w", encoding="utf-8") as f:
        f.write(digest_markdown)


def deliver_digest(
    settings: Settings,
    digest: str,
    line_digest: str,
    run_id: str,
    logger,
    sender_client: GmailClient | None,
) -> None:
    channels = settings.digest.get("channels", ["gmail"])
    subject = f"[Daily Email Digest][multi-account] {run_id}"

    if "gmail" in channels:
        to_email = settings.digest.get("gmail", {}).get("to")
        if to_email and sender_client:
            GmailNotifier(sender_client).send(to_email=to_email, subject=subject, body=digest)
        elif to_email and not sender_client:
            logger.error("gmail digest skipped: no available sender account")

    if "slack_bot" in channels:
        channel_id = settings.digest.get("slack", {}).get("channel_id")
        if channel_id:
            try:
                SlackBotNotifier().send(channel_id=channel_id, text=digest)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("slack delivery failed: %s", exc)

    if "line" in channels:
        line_cfg = settings.digest.get("line", {})
        target_user_id = line_cfg.get("target_user_id") or os.getenv("LINE_TARGET_USER_ID")
        if line_cfg.get("enabled") and target_user_id:
            try:
                LineNotifier().send(user_id=target_user_id, text=line_digest)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("line delivery failed: %s", exc)


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
