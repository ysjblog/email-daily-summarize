import unittest

from src.classifier import classify_messages
from src.config import Settings
from src.models import EmailMessage


def _settings() -> Settings:
    return Settings(
        {
            "whitelist_senders": ["@important.com"],
            "priority_keywords": ["invoice", "驗證碼"],
            "newsletter_sources": ["@news.example.com"],
            "exclude_important_senders": ["@brevo.com"],
            "exclude_important_subject_keywords": ["campaign has been sent"],
            "force_newsletter_senders": ["@vocus.cc"],
            "force_newsletter_subject_keywords": ["最新內容動態"],
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
        self.assertIn("snippet", result.important[0])
        self.assertIn("important score", result.important[0]["reason"])


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
        self.assertIn("gmail promotions label", result.move_candidates[0].reason)
        self.assertEqual(result.move_candidates[0].bucket, "low_priority")

    def test_manual_exclude_sender_overrides_keep(self) -> None:
        msg = EmailMessage(
            id="3",
            thread_id="t3",
            subject="important update",
            sender="campaigns@m.brevo.com",
            to="me@example.com",
            date="",
            snippet="invoice inside",
            body_text="",
            label_ids=["INBOX"],
            internal_ts=0,
        )
        result = classify_messages([msg], _settings())
        self.assertFalse(result.important)
        self.assertEqual(len(result.move_candidates), 1)
        self.assertIn("exclude-important sender", result.move_candidates[0].reason)
        self.assertEqual(result.move_candidates[0].bucket, "low_priority")

    def test_manual_force_newsletter_sender(self) -> None:
        msg = EmailMessage(
            id="4",
            thread_id="t4",
            subject="service update",
            sender="service@vocus.cc",
            to="me@example.com",
            date="",
            snippet="hello",
            body_text="",
            label_ids=["INBOX"],
            internal_ts=0,
        )
        result = classify_messages([msg], _settings())
        self.assertFalse(result.important)
        self.assertEqual(len(result.move_candidates), 1)
        self.assertIn("manual newsletter sender", result.move_candidates[0].reason)
        self.assertEqual(result.move_candidates[0].bucket, "newsletter")
        self.assertEqual(result.newsletter_candidate_ids, {"4"})

    def test_newsletter_sources_are_moved(self) -> None:
        msg = EmailMessage(
            id="5",
            thread_id="t5",
            subject="weekly digest",
            sender="digest@news.example.com",
            to="me@example.com",
            date="",
            snippet="latest stories",
            body_text="",
            label_ids=["INBOX"],
            internal_ts=0,
        )
        result = classify_messages([msg], _settings())
        self.assertFalse(result.important)
        self.assertEqual(len(result.move_candidates), 1)
        self.assertIn("newsletter score", result.move_candidates[0].reason)
        self.assertEqual(result.move_candidates[0].bucket, "newsletter")
        self.assertEqual(result.newsletter_candidate_ids, {"5"})

    def test_move_mode_affects_borderline_case(self) -> None:
        msg = EmailMessage(
            id="6",
            thread_id="t6",
            subject="Friend update",
            sender="friend@community.io",
            to="me@example.com",
            date="",
            snippet="Let us reconnect",
            body_text="",
            label_ids=["INBOX", "CATEGORY_SOCIAL"],
            internal_ts=0,
        )
        aggressive = Settings(
            {
                "move_mode": "aggressive",
                "whitelist_senders": [],
                "priority_keywords": [],
                "newsletter_sources": [],
                "labels": {},
            }
        )
        conservative = Settings(
            {
                "move_mode": "conservative",
                "whitelist_senders": [],
                "priority_keywords": [],
                "newsletter_sources": [],
                "labels": {},
            }
        )

        aggressive_result = classify_messages([msg], aggressive)
        conservative_result = classify_messages([msg], conservative)

        self.assertEqual(len(aggressive_result.move_candidates), 1)
        self.assertFalse(conservative_result.move_candidates)

    def test_scoring_override_can_keep_promotions(self) -> None:
        msg = EmailMessage(
            id="7",
            thread_id="t7",
            subject="special offer",
            sender="promo@shop.com",
            to="me@example.com",
            date="",
            snippet="buy now",
            body_text="",
            label_ids=["INBOX", "CATEGORY_PROMOTIONS"],
            internal_ts=0,
        )
        settings = Settings(
            {
                "whitelist_senders": [],
                "priority_keywords": [],
                "newsletter_sources": [],
                "labels": {},
                "scoring": {
                    "keep_threshold": 1,
                    "move_threshold": -10,
                    "newsletter_threshold": 99,
                },
            }
        )

        result = classify_messages([msg], settings)
        self.assertEqual(len(result.important), 1)
        self.assertFalse(result.move_candidates)

    def test_newsletter_structure_hint_in_body_moves_message(self) -> None:
        msg = EmailMessage(
            id="8",
            thread_id="t8",
            subject="Product update",
            sender="creator@newsletter.example.com",
            to="me@example.com",
            date="",
            snippet="This week we shipped new features.",
            body_text="To unsubscribe, manage preferences at https://example.com/unsubscribe",
            label_ids=["INBOX"],
            internal_ts=0,
        )
        settings = Settings(
            {
                "whitelist_senders": [],
                "priority_keywords": [],
                "newsletter_sources": [],
                "labels": {},
            }
        )

        result = classify_messages([msg], settings)
        self.assertFalse(result.important)
        self.assertEqual(len(result.move_candidates), 1)
        self.assertEqual(result.move_candidates[0].bucket, "newsletter")
        self.assertIn("newsletter score", result.move_candidates[0].reason)


if __name__ == "__main__":
    unittest.main()
