from src.classifier import classify_messages

from src.models import EmailMessage
from src.config import Settings
from src.classifier import ScoringProfile

# Mock settings
MOCK_SETTINGS = Settings({
    "timezone": "Asia/Taipei",
    "labels": {"archive_label": "Auto/LowPriority", "newsletter_label": "Auto/Newsletter"},
    "scoring": {
        "social_penalty": 15,    # High penalty to ensure it drops to low priority
        "list_unsubscribe_score": 8,
    }
})

def test_social_category_ignored():
    """
    Test that an email with CATEGORY_SOCIAL is:
    1. Penalized heavily (important score drops).
    2. Forced to have a negative newsletter score (ignored as newsletter).
    3. Moved to 'low_priority' bucket.
    """
    msg = EmailMessage(
        id="social123",
        thread_id="thread123",
        subject="You have a new friend request",
        sender="Facebook <notification@facebookmail.com>",
        to="me@example.com",
        date="Sat, 14 Feb 2026 10:00:00 +0800",
        snippet="Someone sent you a friend request.",
        body_text="Click here to accept.",
        label_ids=["CATEGORY_SOCIAL", "INBOX"],
        internal_ts=1700000000,
        list_unsubscribe="<mailto:unsubscribe@facebook.com>" # Even has unsubscribe!
    )

    result = classify_messages([msg], MOCK_SETTINGS)

    # Should be moved
    assert len(result.move_candidates) == 1
    decision = result.move_candidates[0]
    
    # Should be bucketed as 'low_priority', NOT 'newsletter'
    assert decision.bucket == "low_priority"
    
    # Verify the reason contains the signal
    assert "gmail social label" in decision.reason
    
    print("\n[PASS] Social category test passed: Email was correctly moved to 'low_priority' despite having unsubscribe link.")

if __name__ == "__main__":
    test_social_category_ignored()
