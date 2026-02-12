import tempfile
import unittest
from pathlib import Path

from src.config import AccountSettings, ConfigError, load_settings


class ConfigTests(unittest.TestCase):
    def test_load_settings_with_multi_account_yaml(self) -> None:
        content = """
timezone: Asia/Taipei
run_times:
  - "09:00"
  - "21:00"
digest:
  channels:
    - gmail
    - slack_bot
accounts:
  - id: work
    display_name: Work Mail
    env_prefix: WORK
    enabled: true
  - id: personal
    display_name: Personal Mail
    env_prefix: PERSONAL
    enabled: false
""".strip()

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.yaml"
            p.write_text(content, encoding="utf-8")
            settings = load_settings(p)

            self.assertEqual(settings.timezone, "Asia/Taipei")
            self.assertEqual(settings.run_times, ["09:00", "21:00"])
            self.assertEqual(len(settings.accounts), 2)
            self.assertEqual(settings.accounts[0].id, "work")
            self.assertEqual(settings.accounts[0].env_prefix, "WORK")
            self.assertFalse(settings.accounts[1].enabled)

    def test_legacy_single_account_compat(self) -> None:
        content = """
timezone: Asia/Taipei
digest:
  channels:
    - gmail
""".strip()

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.yaml"
            p.write_text(content, encoding="utf-8")
            settings = load_settings(p)

            self.assertEqual(len(settings.accounts), 1)
            default_account: AccountSettings = settings.accounts[0]
            self.assertEqual(default_account.id, "default")
            self.assertEqual(default_account.env_prefix, "DEFAULT")

    def test_digest_redaction_mode_default_strict(self) -> None:
        content = """
timezone: Asia/Taipei
digest:
  channels:
    - gmail
accounts:
  - id: work
    env_prefix: WORK
""".strip()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.yaml"
            p.write_text(content, encoding="utf-8")
            settings = load_settings(p)
            self.assertEqual(settings.digest_redaction_mode, "strict")

    def test_digest_redaction_mode_invalid(self) -> None:
        content = """
timezone: Asia/Taipei
digest:
  redaction_mode: unsafe
accounts:
  - id: work
    env_prefix: WORK
""".strip()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "settings.yaml"
            p.write_text(content, encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_settings(p)


if __name__ == "__main__":
    unittest.main()
