from __future__ import annotations

import os
from pathlib import Path

from src.env_utils import upsert_env_values


class AuthFlowError(RuntimeError):
    pass


def env_key(prefix: str, suffix: str) -> str:
    return f"{prefix.upper()}_{suffix}"


def read_client_credentials(prefix: str) -> tuple[str, str]:
    client_id = os.getenv(env_key(prefix, "GMAIL_CLIENT_ID"))
    client_secret = os.getenv(env_key(prefix, "GMAIL_CLIENT_SECRET"))
    if not client_id or not client_secret:
        raise AuthFlowError(
            f"Missing OAuth client credentials for prefix={prefix}. "
            f"Expected {env_key(prefix, 'GMAIL_CLIENT_ID')} and {env_key(prefix, 'GMAIL_CLIENT_SECRET')}"
        )
    return client_id, client_secret


def obtain_refresh_token(client_id: str, client_secret: str, login_hint: str | None = None) -> str:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ModuleNotFoundError as exc:
        raise AuthFlowError("google-auth-oauthlib is required for auth login") from exc

    scopes = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
    kwargs = {
        "access_type": "offline",
        "prompt": "consent",
    }
    if login_hint:
        kwargs["login_hint"] = login_hint

    credentials = flow.run_local_server(port=0, **kwargs)
    if not credentials.refresh_token:
        raise AuthFlowError("OAuth flow succeeded but no refresh token returned")

    return credentials.refresh_token


def save_refresh_token(env_path: str | Path, prefix: str, refresh_token: str) -> str:
    key = env_key(prefix, "GMAIL_REFRESH_TOKEN")
    upsert_env_values(env_path, {key: refresh_token})
    return key
