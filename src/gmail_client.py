from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Any

import requests

from src.models import EmailMessage


class GmailAuthError(RuntimeError):
    pass


class GmailClient:
    BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, timeout: int = 30):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.timeout = timeout
        self._access_token: str | None = None

    @classmethod
    def from_env_prefix(cls, prefix: str, timeout: int = 30) -> "GmailClient":
        normalized = prefix.upper()
        client_id = os.getenv(f"{normalized}_GMAIL_CLIENT_ID")
        client_secret = os.getenv(f"{normalized}_GMAIL_CLIENT_SECRET")
        refresh_token = os.getenv(f"{normalized}_GMAIL_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise GmailAuthError(
                "Missing Gmail OAuth env vars for prefix="
                f"{normalized}. Expected {normalized}_GMAIL_CLIENT_ID, "
                f"{normalized}_GMAIL_CLIENT_SECRET, {normalized}_GMAIL_REFRESH_TOKEN"
            )

        return cls(client_id=client_id, client_secret=client_secret, refresh_token=refresh_token, timeout=timeout)

    def _refresh_access_token(self) -> str:
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if not token:
            raise GmailAuthError("Unable to refresh Gmail access token")
        self._access_token = token
        return token

    def _headers(self) -> dict[str, str]:
        token = self._access_token or self._refresh_access_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.BASE_URL}{path}"
        resp = requests.request(method, url, headers=self._headers(), timeout=self.timeout, **kwargs)
        if resp.status_code == 401:
            self._refresh_access_token()
            resp = requests.request(method, url, headers=self._headers(), timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp

    def list_messages(self, query: str, label_ids: list[str] | None = None, max_results: int = 200) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        page_token: str | None = None

        while True:
            payload: dict[str, Any] = {"q": query, "maxResults": min(max_results, 500)}
            if label_ids:
                payload["labelIds"] = label_ids
            if page_token:
                payload["pageToken"] = page_token

            resp = self._request("GET", "/messages", params=payload)
            body = resp.json()
            messages.extend(body.get("messages", []))

            page_token = body.get("nextPageToken")
            if not page_token or len(messages) >= max_results:
                break

        return messages[:max_results]

    def get_message(self, message_id: str) -> EmailMessage:
        resp = self._request("GET", f"/messages/{message_id}", params={"format": "full"})
        raw = resp.json()
        payload = raw.get("payload", {})
        headers = payload.get("headers", [])

        def find_header(name: str) -> str:
            for h in headers:
                if h.get("name", "").lower() == name.lower():
                    return h.get("value", "")
            return ""

        body_text = self._extract_body(payload)
        ts = int(raw.get("internalDate", "0"))

        return EmailMessage(
            id=raw.get("id", message_id),
            thread_id=raw.get("threadId", ""),
            subject=find_header("Subject"),
            sender=find_header("From"),
            to=find_header("To"),
            date=find_header("Date") or datetime.utcfromtimestamp(ts / 1000).isoformat(),
            snippet=raw.get("snippet", ""),
            body_text=body_text,
            label_ids=raw.get("labelIds", []),
            internal_ts=ts,
        )

    def _extract_body(self, payload: dict[str, Any]) -> str:
        body = payload.get("body", {})
        if body.get("data"):
            return self._decode_base64(body["data"])

        parts = payload.get("parts", [])
        for part in parts:
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                return self._decode_base64(part["body"]["data"])
            nested = self._extract_body(part)
            if nested:
                return nested

        return ""

    @staticmethod
    def _decode_base64(data: str) -> str:
        pad = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(data + pad)
        return decoded.decode("utf-8", errors="replace")

    def modify_labels(self, message_id: str, add_label_ids: list[str] | None = None, remove_label_ids: list[str] | None = None) -> None:
        payload = {
            "addLabelIds": add_label_ids or [],
            "removeLabelIds": remove_label_ids or [],
        }
        self._request("POST", f"/messages/{message_id}/modify", json=payload)

    def list_labels(self) -> list[dict[str, Any]]:
        resp = self._request("GET", "/labels")
        return resp.json().get("labels", [])

    def get_or_create_label_id(self, label_name: str) -> str:
        labels = self.list_labels()
        for label in labels:
            if label.get("name") == label_name:
                return label.get("id")

        resp = self._request(
            "POST",
            "/labels",
            json={
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        return resp.json()["id"]

    def send_email(self, to_email: str, subject: str, body: str) -> None:
        raw_message = f"To: {to_email}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}"
        encoded = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("utf-8")
        self._request("POST", "/messages/send", json={"raw": encoded})
