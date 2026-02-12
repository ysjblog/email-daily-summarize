from __future__ import annotations

from src.gmail_client import GmailClient


class GmailNotifier:
    def __init__(self, gmail_client: GmailClient):
        self.gmail_client = gmail_client

    def send(self, to_email: str, subject: str, body: str) -> None:
        self.gmail_client.send_email(to_email=to_email, subject=subject, body=body)
