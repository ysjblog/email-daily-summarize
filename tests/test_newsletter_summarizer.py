import unittest

from src.config import Settings
from src.models import EmailMessage
from src.newsletter_summarizer import summarize_newsletters


class NewsletterSummarizerTests(unittest.TestCase):
    def test_newsletter_summary_keeps_each_message(self) -> None:
        settings = Settings(
            {
                "newsletter_sources": ["@substack.com"],
                "whitelist_senders": [],
                "priority_keywords": [],
                "labels": {},
            }
        )

        msg1 = EmailMessage(
            id="n1",
            thread_id="tn1",
            subject="Weekly Tech Digest",
            sender="daily@substack.com",
            to="me@example.com",
            date="",
            snippet="Top 5 stories this week. https://example.com/story1",
            body_text="Story A has major updates. Story B is about AI safety.",
            label_ids=["INBOX"],
            internal_ts=0,
        )

        msg2 = EmailMessage(
            id="n2",
            thread_id="tn2",
            subject="Another issue",
            sender="daily@substack.com",
            to="me@example.com",
            date="",
            snippet="duplicate sender",
            body_text="",
            label_ids=["INBOX"],
            internal_ts=0,
        )

        summaries = summarize_newsletters([msg1, msg2], settings)
        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0].subject, "Weekly Tech Digest")
        self.assertEqual(summaries[1].subject, "Another issue")
        self.assertTrue(summaries[0].links)
        self.assertTrue(summaries[0].bullets)

    def test_newsletter_summary_heuristic_match(self) -> None:
        settings = Settings(
            {
                "newsletter_sources": [],
                "whitelist_senders": [],
                "priority_keywords": [],
                "labels": {},
            }
        )

        msg = EmailMessage(
            id="n3",
            thread_id="tn3",
            subject="Weekly Digest: Product Highlights",
            sender="updates@service.io",
            to="me@example.com",
            date="",
            snippet="This week's top stories",
            body_text="Story one details and story two details.",
            label_ids=["INBOX"],
            internal_ts=0,
        )

        summaries = summarize_newsletters([msg], settings)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].subject, msg.subject)

    def test_newsletter_summary_excludes_transactional_messages(self) -> None:
        settings = Settings(
            {
                "newsletter_sources": [],
                "whitelist_senders": [],
                "priority_keywords": [],
                "labels": {},
            }
        )

        msg = EmailMessage(
            id="n4",
            thread_id="tn4",
            subject="Monthly newsletter invoice receipt",
            sender="billing@service.io",
            to="me@example.com",
            date="",
            snippet="Your invoice is ready",
            body_text="Please review billing details.",
            label_ids=["INBOX", "CATEGORY_PROMOTIONS"],
            internal_ts=0,
        )

        summaries = summarize_newsletters([msg], settings)
        self.assertEqual(len(summaries), 0)


if __name__ == "__main__":
    unittest.main()
