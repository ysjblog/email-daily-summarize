
from src.models import EmailMessage
from src.classifier import _score_message, ScoringProfile, ScoreState, _decision_from_score
from src.config import Settings

def test_promotion_scoring():
    msg = EmailMessage(
        id="test",
        thread_id="thread",
        subject="Super Sale",
        sender="shop@example.com",
        to="me@example.com",
        date="2023-01-01",
        snippet="Buy now",
        body_text="Buy now",
        label_ids=["CATEGORY_PROMOTIONS"],
        internal_ts=0,
        list_unsubscribe="<mailto:unsub@example.com>" # Even with this, it should be ignored
    )
    
    settings = Settings(raw={})
    profile = ScoringProfile(
        list_unsubscribe_score=10, 
        promotion_penalty=10,
        newsletter_threshold=3,
        keep_threshold=3
    )
    
    score = _score_message(msg, settings, set(), profile)
    decision = _decision_from_score(score, profile)
    
    print(f"Important Score: {score.important}")
    print(f"Newsletter Score: {score.newsletter}")
    print(f"Signals: {score.move_signals}")
    print(f"Decision: {decision}")

    assert decision["bucket"] == "low_priority"
    assert score.newsletter < 0

if __name__ == "__main__":
    test_promotion_scoring()
