from __future__ import annotations

import os

import requests


class SlackNotifyError(RuntimeError):
    pass


class SlackBotNotifier:
    API = "https://slack.com/api/chat.postMessage"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def send(self, channel_id: str, text: str) -> None:
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            raise SlackNotifyError("SLACK_BOT_TOKEN is missing")

        response = requests.post(
            self.API,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={"channel": channel_id, "text": text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise SlackNotifyError(payload.get("error", "unknown Slack API error"))
