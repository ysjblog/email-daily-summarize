from __future__ import annotations

import json
from pathlib import Path

from src.models import State


class StateStore:
    def __init__(self, account_id: str = "default", base_dir: str | Path = "data/state") -> None:
        self.account_id = account_id
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / f"{self.account_id}.json"

    def load(self) -> State:
        if not self.path.exists():
            return State.empty()

        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        return State(
            last_successful_run=raw.get("last_successful_run"),
            processed_message_ids=raw.get("processed_message_ids", []),
            last_slack_error=raw.get("last_slack_error"),
        )

    def save(self, state: State) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_successful_run": state.last_successful_run,
            "processed_message_ids": state.processed_message_ids[-5000:],
            "last_slack_error": state.last_slack_error,
        }
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
