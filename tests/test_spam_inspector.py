import unittest

from src.config import Settings
from src.models import EmailMessage
from src.spam_inspector import inspect_spam_messages


def _settings() -> Settings:
    return Settings(
        {
            "whitelist_senders": ["@trusted.com"],
            "priority_keywords": ["invoice", "驗證碼", "security alert"],
            "newsletter_sources": [],
            "labels": {},
        }
    )


class SpamInspectorTests(unittest.TestCase):
    def test_spam_high_score_detected(self) -> None:
        msg = EmailMessage(
            id="spam-1",
            thread_id="ts1",
            subject="Security alert and invoice required today",
            sender="ops@trusted.com",
            to="me@example.com",
            date="",
            snippet="Please verify billing now",
            body_text="deadline today",
            label_ids=["SPAM"],
            internal_ts=0,
        )

        findings = inspect_spam_messages([msg], _settings(), trusted_senders={"ops@trusted.com"})
        self.assertEqual(len(findings), 1)
        self.assertGreaterEqual(findings[0].score, 70)


    def test_spam_low_score_filtered_out(self) -> None:
        msg = EmailMessage(
            id="spam-2",
            thread_id="ts2",
            subject="funny meme",
            sender="x@unknown.com",
            to="me@example.com",
            date="",
            snippet="just for fun",
            body_text="",
            label_ids=["SPAM"],
            internal_ts=0,
        )
        findings = inspect_spam_messages([msg], _settings(), trusted_senders=set())
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
