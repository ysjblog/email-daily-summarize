import unittest
from unittest.mock import Mock, patch

from src.config import Settings
from src.main import run_all_accounts
from src.models import RunReport


def _settings() -> Settings:
    return Settings(
        {
            "timezone": "Asia/Taipei",
            "digest": {
                "channels": ["gmail", "slack_bot", "line"],
                "gmail": {"to": "me@example.com"},
                "slack": {"channel_id": "C123"},
                "line": {"enabled": True, "target_user_id": "U123"},
            },
            "accounts": [
                {
                    "id": "work",
                    "display_name": "Work",
                    "env_prefix": "WORK",
                    "enabled": True,
                },
                {
                    "id": "personal",
                    "display_name": "Personal",
                    "env_prefix": "PERSONAL",
                    "enabled": True,
                },
            ],
        }
    )


def _report(account_id: str, display_name: str) -> RunReport:
    return RunReport(
        run_id="2026-02-12-0900",
        mode="dry-run",
        started_at="2026-02-12T01:00:00Z",
        finished_at="2026-02-12T01:00:01Z",
        window_start="2026-02-12T00:00:00+08:00",
        window_end="2026-02-12T01:00:00+08:00",
        account_id=account_id,
        display_name=display_name,
        important=[{"subject": "A", "sender": "x", "reason": "keep"}],
        moved=[],
        spam_suspects=[],
        newsletters=[],
        errors=[],
    )


class MainMultiAccountTests(unittest.TestCase):
    @patch("src.main.deliver_digest")
    @patch("src.main.write_combined_reports")
    @patch("src.main.write_account_reports")
    @patch("src.main.execute_account")
    def test_run_all_accounts_success(
        self,
        execute_account_mock: Mock,
        _write_account_reports: Mock,
        write_combined_reports_mock: Mock,
        deliver_digest_mock: Mock,
    ) -> None:
        execute_account_mock.side_effect = [
            (_report("work", "Work"), object()),
            (_report("personal", "Personal"), object()),
        ]

        result = run_all_accounts(_settings(), dry_run=True, target_account=None)

        self.assertEqual(result["success"], ["work", "personal"])
        self.assertEqual(result["failed"], [])
        self.assertEqual(execute_account_mock.call_count, 2)
        write_combined_reports_mock.assert_called_once()
        deliver_digest_mock.assert_called_once()

    @patch("src.main.deliver_digest")
    @patch("src.main.write_combined_reports")
    @patch("src.main.write_account_reports")
    @patch("src.main.execute_account")
    def test_run_all_accounts_partial_failure(
        self,
        execute_account_mock: Mock,
        write_account_reports_mock: Mock,
        _write_combined_reports: Mock,
        _deliver_digest: Mock,
    ) -> None:
        execute_account_mock.side_effect = [
            RuntimeError("work failed"),
            (_report("personal", "Personal"), object()),
        ]

        result = run_all_accounts(_settings(), dry_run=True, target_account=None)

        self.assertEqual(result["success"], ["personal"])
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(result["failed"][0]["account_id"], "work")
        self.assertEqual(execute_account_mock.call_count, 2)
        write_account_reports_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
