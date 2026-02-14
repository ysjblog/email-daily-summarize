from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class EmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    to: str
    date: str
    snippet: str
    body_text: str
    label_ids: list[str]
    internal_ts: int
    list_unsubscribe: str | None = None


@dataclass(slots=True)
class MoveDecision:
    message_id: str
    subject: str
    sender: str
    reason: str
    bucket: str = "low_priority"


@dataclass(slots=True)
class SpamFinding:
    message_id: str
    subject: str
    sender: str
    score: int
    reasons: list[str]


@dataclass(slots=True)
class NewsletterSummary:
    source: str
    subject: str
    bullets: list[str]
    links: list[str]


@dataclass(slots=True)
class RunReport:
    run_id: str
    mode: str
    started_at: str
    finished_at: str
    window_start: str
    window_end: str
    account_id: str
    display_name: str
    important: list[dict] = field(default_factory=list)
    moved: list[dict] = field(default_factory=list)
    spam_suspects: list[dict] = field(default_factory=list)
    newsletters: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class State:
    last_successful_run: str | None
    processed_message_ids: list[str]
    last_slack_error: str | None

    @staticmethod
    def empty() -> "State":
        return State(
            last_successful_run=None,
            processed_message_ids=[],
            last_slack_error=None,
        )



def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
