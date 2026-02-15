
from src.models import EmailMessage
from src.classifier import _score_message, ScoringProfile, ScoreState
from src.config import Settings

def test_header_scoring():
    msg = EmailMessage(
        id="test",
        thread_id="thread",
        subject="Newsletter",
        sender="sender@example.com",
        to="me@example.com",
        date="2023-01-01",
        snippet="content",
        body_text="content",
        label_ids=[],
        internal_ts=0,
        list_unsubscribe="<mailto:unsubscribe@example.com>"
    )
    
    settings = Settings(raw={})
    profile = ScoringProfile(list_unsubscribe_score=10, newsletter_source_penalty=5)
    
    score = _score_message(msg, settings, set(), profile)
    
    print(f"Important Score: {score.important}")
    print(f"Newsletter Score: {score.newsletter}")
    print(f"Signals: {score.move_signals}")

    assert "list-unsubscribe header found" in score.move_signals
    assert score.newsletter >= 10

if __name__ == "__main__":
    test_header_scoring()
