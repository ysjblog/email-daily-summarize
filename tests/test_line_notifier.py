import os
import unittest
from unittest.mock import Mock, patch

from src.notifiers.line_notifier import LineNotifyError, LineNotifier


class LineNotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
        os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "line-token"

    def tearDown(self) -> None:
        if self.original is None:
            os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)
        else:
            os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = self.original

    @patch("src.notifiers.line_notifier.requests.post")
    def test_send_payload(self, post_mock: Mock) -> None:
        response = Mock()
        response.text = "{}"
        response.json.return_value = {}
        response.raise_for_status.return_value = None
        post_mock.return_value = response

        LineNotifier().send(user_id="U123", text="hello")

        _, kwargs = post_mock.call_args
        self.assertEqual(kwargs["json"]["to"], "U123")
        self.assertEqual(kwargs["json"]["messages"][0]["type"], "text")

    def test_missing_token(self) -> None:
        os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)
        with self.assertRaises(LineNotifyError):
            LineNotifier().send(user_id="U123", text="hello")


if __name__ == "__main__":
    unittest.main()
