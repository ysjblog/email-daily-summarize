import unittest

from src.classifier import classify_messages
from src.config import Settings
from src.models import EmailMessage


def _settings() -> Settings:
    return Settings(
        {
            "whitelist_senders": ["@important.com"],
            "priority_keywords": ["invoice", "驗證碼"],
            "newsletter_sources": [],
            "labels": {},
        }
    )


class ClassifierTests(unittest.TestCase):
    def test_keep_whitelist_sender(self) -> None:
        msg = EmailMessage(
            id="1",
            thread_id="t1",
            subject="hello",
            sender="boss@important.com",
            to="me@example.com",
            date="",
            snippet="",
            body_text="",
            label_ids=["INBOX"],
            internal_ts=0,
        )
        result = classify_messages([msg], _settings())
        self.assertEqual(len(result.important), 1)
        self.assertFalse(result.move_candidates)


    def test_move_promotions(self) -> None:
        msg = EmailMessage(
            id="2",
            thread_id="t2",
            subject="special offer",
            sender="promo@shop.com",
            to="me@example.com",
            date="",
            snippet="buy now",
            body_text="",
            label_ids=["INBOX", "CATEGORY_PROMOTIONS"],
            internal_ts=0,
        )
        result = classify_messages([msg], _settings())
        self.assertEqual(len(result.move_candidates), 1)
        self.assertTrue(result.move_candidates[0].reason.startswith("gmail category"))


if __name__ == "__main__":
    unittest.main()
