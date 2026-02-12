from __future__ import annotations

import os

import requests


class LineNotifyError(RuntimeError):
    pass


class LineNotifier:
    API = "https://api.line.me/v2/bot/message/push"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def send(self, user_id: str, text: str) -> None:
        token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if not token:
            raise LineNotifyError("LINE_CHANNEL_ACCESS_TOKEN is missing")

        response = requests.post(
            self.API,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "to": user_id,
                "messages": [{"type": "text", "text": text[:4900]}],
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        if response.text.strip():
            payload = response.json()
            if payload.get("message"):
                raise LineNotifyError(payload.get("message", "unknown LINE API error"))
