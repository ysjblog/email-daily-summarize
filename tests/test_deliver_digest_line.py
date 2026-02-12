import os
import unittest
from unittest.mock import Mock, patch

from src.config import Settings
from src.main import deliver_digest


def _settings(target_user_id: str | None) -> Settings:
    line_cfg = {"enabled": True}
    if target_user_id:
        line_cfg["target_user_id"] = target_user_id
    return Settings({"digest": {"channels": ["line"], "line": line_cfg}})


class DeliverDigestLineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = os.environ.get("LINE_TARGET_USER_ID")

    def tearDown(self) -> None:
        if self.original is None:
            os.environ.pop("LINE_TARGET_USER_ID", None)
        else:
            os.environ["LINE_TARGET_USER_ID"] = self.original

    @patch("src.main.LineNotifier.send")
    def test_line_target_prefers_env(self, line_send_mock: Mock) -> None:
        os.environ["LINE_TARGET_USER_ID"] = "U_ENV"
        settings = _settings("U_YAML")

        deliver_digest(
            settings=settings,
            digest="d",
            line_digest="line",
            run_id="r",
            logger=Mock(),
            sender_client=None,
        )

        line_send_mock.assert_called_once_with(user_id="U_ENV", text="line")

    @patch("src.main.LineNotifier.send")
    def test_line_target_fallback_to_yaml(self, line_send_mock: Mock) -> None:
        os.environ.pop("LINE_TARGET_USER_ID", None)
        settings = _settings("U_YAML")

        deliver_digest(
            settings=settings,
            digest="d",
            line_digest="line",
            run_id="r",
            logger=Mock(),
            sender_client=None,
        )

        line_send_mock.assert_called_once_with(user_id="U_YAML", text="line")


if __name__ == "__main__":
    unittest.main()
