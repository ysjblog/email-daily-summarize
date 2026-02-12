from argparse import Namespace
from datetime import datetime
import unittest
from unittest.mock import Mock, patch

from src.config import Settings
from src.main import main, parse_args, run_all_accounts
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
    def test_parse_args_uses_secure_default_env_file(self) -> None:
        with patch("sys.argv", ["prog", "dry-run"]):
            args = parse_args()
        self.assertEqual(args.env_file, "~/.config/daily-summarize/secrets.env")

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

    @patch("src.main.deliver_digest")
    @patch("src.main.write_combined_reports")
    @patch("src.main.write_account_reports")
    @patch("src.main.execute_account")
    def test_run_all_accounts_skip_digest_when_send_digest_false(
        self,
        execute_account_mock: Mock,
        _write_account_reports: Mock,
        _write_combined_reports: Mock,
        deliver_digest_mock: Mock,
    ) -> None:
        execute_account_mock.side_effect = [
            (_report("work", "Work"), object()),
            (_report("personal", "Personal"), object()),
        ]

        run_all_accounts(_settings(), dry_run=True, target_account=None, send_digest=False)

        deliver_digest_mock.assert_not_called()

    def test_main_backfill_default_no_notify(self) -> None:
        args = Namespace(
            cmd="backfill",
            days=2,
            account=None,
            notify=False,
            config="config/settings.yaml",
            env_file=".env",
        )
        settings = Settings(
            {
                "timezone": "Asia/Taipei",
                "digest": {},
                "accounts": [{"id": "work", "display_name": "Work", "env_prefix": "WORK", "enabled": True}],
            }
        )

        with (
            patch("src.main.parse_args", return_value=args),
            patch("src.main.load_env_into_os"),
            patch("src.main.load_settings", return_value=settings),
            patch("src.main.build_logger", return_value=Mock(name="daily-summarize")),
            patch("src.main.run_all_accounts") as run_all_accounts_mock,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_all_accounts_mock.call_count, 2)
        for call in run_all_accounts_mock.call_args_list:
            self.assertTrue(call.kwargs["dry_run"])
            self.assertFalse(call.kwargs["send_digest"])

    def test_main_backfill_notify_enabled(self) -> None:
        args = Namespace(
            cmd="backfill",
            days=1,
            account=None,
            notify=True,
            config="config/settings.yaml",
            env_file=".env",
        )
        settings = Settings(
            {
                "timezone": "Asia/Taipei",
                "digest": {},
                "accounts": [{"id": "work", "display_name": "Work", "env_prefix": "WORK", "enabled": True}],
            }
        )

        with (
            patch("src.main.parse_args", return_value=args),
            patch("src.main.load_env_into_os"),
            patch("src.main.load_settings", return_value=settings),
            patch("src.main.build_logger", return_value=Mock(name="daily-summarize")),
            patch("src.main.run_all_accounts") as run_all_accounts_mock,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        run_all_accounts_mock.assert_called_once()
        self.assertTrue(run_all_accounts_mock.call_args.kwargs["send_digest"])

    def test_main_run_with_hours_sets_window(self) -> None:
        fixed_now = datetime(2026, 2, 12, 10, 0, 0)
        args = Namespace(
            cmd="run",
            account=None,
            hours=24,
            config="config/settings.yaml",
            env_file=".env",
        )
        settings = Settings(
            {
                "timezone": "Asia/Taipei",
                "digest": {},
                "accounts": [{"id": "work", "display_name": "Work", "env_prefix": "WORK", "enabled": True}],
            }
        )

        with (
            patch("src.main.parse_args", return_value=args),
            patch("src.main.load_env_into_os"),
            patch("src.main.load_settings", return_value=settings),
            patch("src.main.build_logger", return_value=Mock(name="daily-summarize")),
            patch("src.main.datetime") as datetime_mock,
            patch("src.main.run_all_accounts") as run_all_accounts_mock,
        ):
            datetime_mock.now.return_value = fixed_now
            exit_code = main()

        self.assertEqual(exit_code, 0)
        run_all_accounts_mock.assert_called_once()
        kwargs = run_all_accounts_mock.call_args.kwargs
        self.assertEqual(kwargs["window_end"], fixed_now)
        self.assertEqual(kwargs["window_start"], fixed_now.replace(day=11))

    def test_main_dry_run_without_hours_uses_state_window(self) -> None:
        args = Namespace(
            cmd="dry-run",
            account=None,
            hours=None,
            config="config/settings.yaml",
            env_file=".env",
        )
        settings = Settings(
            {
                "timezone": "Asia/Taipei",
                "digest": {},
                "accounts": [{"id": "work", "display_name": "Work", "env_prefix": "WORK", "enabled": True}],
            }
        )

        with (
            patch("src.main.parse_args", return_value=args),
            patch("src.main.load_env_into_os"),
            patch("src.main.load_settings", return_value=settings),
            patch("src.main.build_logger", return_value=Mock(name="daily-summarize")),
            patch("src.main.run_all_accounts") as run_all_accounts_mock,
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        run_all_accounts_mock.assert_called_once()
        kwargs = run_all_accounts_mock.call_args.kwargs
        self.assertIsNone(kwargs["window_start"])
        self.assertIsNone(kwargs["window_end"])


if __name__ == "__main__":
    unittest.main()
