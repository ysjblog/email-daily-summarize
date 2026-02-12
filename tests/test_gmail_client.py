import os
import unittest

from src.gmail_client import GmailAuthError, GmailClient


class GmailClientEnvTests(unittest.TestCase):
    def test_from_env_prefix_success(self) -> None:
        os.environ["WORK_GMAIL_CLIENT_ID"] = "cid"
        os.environ["WORK_GMAIL_CLIENT_SECRET"] = "sec"
        os.environ["WORK_GMAIL_REFRESH_TOKEN"] = "ref"

        client = GmailClient.from_env_prefix("WORK")
        self.assertEqual(client.client_id, "cid")

    def test_from_env_prefix_missing(self) -> None:
        os.environ.pop("MISS_GMAIL_CLIENT_ID", None)
        os.environ.pop("MISS_GMAIL_CLIENT_SECRET", None)
        os.environ.pop("MISS_GMAIL_REFRESH_TOKEN", None)

        with self.assertRaises(GmailAuthError):
            GmailClient.from_env_prefix("MISS")


if __name__ == "__main__":
    unittest.main()
