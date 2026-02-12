from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from src.classifier import ClassificationResult
from src.config import AccountSettings, Settings
from src.main import execute_account
from src.models import EmailMessage, MoveDecision, State


class ExecuteAccountTests(unittest.TestCase):
    @patch("src.main.write_account_reports")
    @patch("src.main.build_combined_digest", return_value="")
    @patch("src.main.summarize_newsletters", return_value=[])
    @patch("src.main.inspect_spam_messages", return_value=[])
    @patch("src.main.classify_messages")
    @patch("src.main.fetch_messages")
    @patch("src.main.StateStore")
    @patch("src.main.GmailClient.from_env_prefix")
    @patch("src.main.utc_now_iso", return_value="2026-02-12T08:00:00Z")
    def test_execute_account_routes_bucket_to_correct_label(
        self,
        _utc_now_iso: Mock,
        gmail_from_env_mock: Mock,
        state_store_cls_mock: Mock,
        fetch_messages_mock: Mock,
        classify_messages_mock: Mock,
        _inspect_spam_messages: Mock,
        summarize_newsletters_mock: Mock,
        _build_combined_digest: Mock,
        _write_account_reports: Mock,
    ) -> None:
        settings = Settings(
            {
                "timezone": "Asia/Taipei",
                "labels": {
                    "archive_label": "Auto/LowPriority",
                    "newsletter_label": "Auto/Newsletter",
                },
                "spam_scan": {"enabled": False},
                "accounts": [{"id": "work", "display_name": "Work", "env_prefix": "WORK", "enabled": True}],
            }
        )
        account = AccountSettings(id="work", display_name="Work", env_prefix="WORK", enabled=True, overrides={})

        newsletter_msg = EmailMessage(
            id="n1",
            thread_id="tn1",
            subject="Weekly digest",
            sender="news@example.com",
            to="me@example.com",
            date="",
            snippet="top stories",
            body_text="content",
            label_ids=["INBOX", "CATEGORY_PROMOTIONS"],
            internal_ts=0,
        )
        low_priority_msg = EmailMessage(
            id="n2",
            thread_id="tn2",
            subject="special offer",
            sender="promo@example.com",
            to="me@example.com",
            date="",
            snippet="sale",
            body_text="",
            label_ids=["INBOX", "CATEGORY_PROMOTIONS"],
            internal_ts=0,
        )

        fetch_messages_mock.side_effect = [[newsletter_msg, low_priority_msg], []]

        classified = ClassificationResult()
        classified.important = []
        classified.newsletter_candidate_ids = {"n1"}
        classified.move_candidates = [
            MoveDecision(
                message_id="n1",
                subject=newsletter_msg.subject,
                sender=newsletter_msg.sender,
                reason="newsletter score",
                bucket="newsletter",
            ),
            MoveDecision(
                message_id="n2",
                subject=low_priority_msg.subject,
                sender=low_priority_msg.sender,
                reason="low-priority score",
                bucket="low_priority",
            ),
        ]
        classify_messages_mock.return_value = classified

        gmail_mock = Mock()

        def _label_id(name: str) -> str:
            mapping = {
                "Auto/LowPriority": "LBL_ARCHIVE",
                "Auto/Newsletter": "LBL_NEWSLETTER",
            }
            return mapping[name]

        gmail_mock.get_or_create_label_id.side_effect = _label_id
        gmail_from_env_mock.return_value = gmail_mock

        state_store = Mock()
        state_store.load.return_value = State.empty()
        state_store_cls_mock.return_value = state_store

        report, _ = execute_account(
            settings=settings,
            account=account,
            dry_run=False,
            run_id="2026-02-12-1600",
            window_start=None,
            window_end=None,
            logger_name="daily-summarize-test",
        )

        self.assertEqual(len(report.moved), 2)
        self.assertEqual(report.moved[0]["bucket"], "newsletter")
        self.assertEqual(report.moved[1]["bucket"], "low_priority")
        summarize_newsletters_mock.assert_called_once()
        summarized_messages = summarize_newsletters_mock.call_args.args[0]
        self.assertEqual([msg.id for msg in summarized_messages], ["n1"])
        self.assertTrue(summarize_newsletters_mock.call_args.kwargs["preclassified"])
        self.assertEqual(
            gmail_mock.modify_labels.call_args_list[0].kwargs["add_label_ids"],
            ["LBL_NEWSLETTER"],
        )
        self.assertEqual(
            gmail_mock.modify_labels.call_args_list[1].kwargs["add_label_ids"],
            ["LBL_ARCHIVE"],
        )


if __name__ == "__main__":
    unittest.main()
