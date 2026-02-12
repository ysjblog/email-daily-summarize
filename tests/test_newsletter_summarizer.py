import unittest

from src.config import Settings
from src.models import EmailMessage
from src.newsletter_summarizer import summarize_newsletters


class NewsletterSummarizerTests(unittest.TestCase):
    def test_newsletter_summary_and_dedup(self) -> None:
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
        self.assertEqual(len(summaries), 1)
        self.assertTrue(summaries[0].links)
        self.assertTrue(summaries[0].bullets)


if __name__ == "__main__":
    unittest.main()
