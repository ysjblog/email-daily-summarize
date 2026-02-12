import os
import tempfile
import unittest
from pathlib import Path

from src.auth.google_oauth import AuthFlowError, env_key, read_client_credentials, save_refresh_token


class AuthLoginTests(unittest.TestCase):
    def test_save_refresh_token_to_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("WORK_GMAIL_CLIENT_ID=abc\n", encoding="utf-8")

            key = save_refresh_token(env_path, "WORK", "refresh-token-123")
            content = env_path.read_text(encoding="utf-8")

            self.assertEqual(key, "WORK_GMAIL_REFRESH_TOKEN")
            self.assertIn("WORK_GMAIL_CLIENT_ID=abc", content)
            self.assertIn("WORK_GMAIL_REFRESH_TOKEN=refresh-token-123", content)

    def test_read_client_credentials_missing(self) -> None:
        key_id = env_key("WORK", "GMAIL_CLIENT_ID")
        key_secret = env_key("WORK", "GMAIL_CLIENT_SECRET")
        backup_id = os.environ.pop(key_id, None)
        backup_secret = os.environ.pop(key_secret, None)

        try:
            with self.assertRaises(AuthFlowError):
                read_client_credentials("WORK")
        finally:
            if backup_id is not None:
                os.environ[key_id] = backup_id
            if backup_secret is not None:
                os.environ[key_secret] = backup_secret


if __name__ == "__main__":
    unittest.main()
