import unittest

from src.config_ui_server import _apply_action, _render_page


class ConfigUIServerTests(unittest.TestCase):
    def test_apply_action_global_add_and_remove(self) -> None:
        raw = {"whitelist_senders": ["a@example.com"], "newsletter_sources": []}

        _apply_action(raw, "add_global_whitelist", "b@example.com", "")
        _apply_action(raw, "add_global_newsletter", "@substack.com", "")
        _apply_action(raw, "remove_global_whitelist", "a@example.com", "")

        self.assertEqual(raw["whitelist_senders"], ["b@example.com"])
        self.assertEqual(raw["newsletter_sources"], ["@substack.com"])

    def test_apply_action_global_exclude_and_force_newsletter_rules(self) -> None:
        raw = {}

        _apply_action(raw, "add_global_exclude_important_sender", "@brevo.com", "")
        _apply_action(raw, "add_global_exclude_important_subject", "campaign has been sent", "")
        _apply_action(raw, "add_global_force_newsletter_sender", "@vocus.cc", "")
        _apply_action(raw, "add_global_force_newsletter_subject", "最新內容動態", "")

        self.assertEqual(raw["exclude_important_senders"], ["@brevo.com"])
        self.assertEqual(raw["exclude_important_subject_keywords"], ["campaign has been sent"])
        self.assertEqual(raw["force_newsletter_senders"], ["@vocus.cc"])
        self.assertEqual(raw["force_newsletter_subject_keywords"], ["最新內容動態"])

    def test_apply_action_account_override_add_and_remove(self) -> None:
        raw = {"accounts": [{"id": "work", "overrides": {"whitelist_senders": ["ceo@company.com"]}}]}

        _apply_action(raw, "add_account_whitelist", "boss@company.com", "work")
        _apply_action(raw, "remove_account_whitelist", "ceo@company.com", "work")
        _apply_action(raw, "add_account_newsletter", "newsletter@site.com", "work")

        overrides = raw["accounts"][0]["overrides"]
        self.assertEqual(overrides["whitelist_senders"], ["boss@company.com"])
        self.assertEqual(overrides["newsletter_sources"], ["newsletter@site.com"])

    def test_apply_action_account_override_exclude_and_force_newsletter(self) -> None:
        raw = {"accounts": [{"id": "work", "overrides": {}}]}

        _apply_action(raw, "add_account_exclude_important_sender", "campaigns@m.brevo.com", "work")
        _apply_action(raw, "add_account_exclude_important_subject", "confirmation", "work")
        _apply_action(raw, "add_account_force_newsletter_sender", "service@vocus.cc", "work")
        _apply_action(raw, "add_account_force_newsletter_subject", "最新內容動態", "work")

        overrides = raw["accounts"][0]["overrides"]
        self.assertEqual(overrides["exclude_important_senders"], ["campaigns@m.brevo.com"])
        self.assertEqual(overrides["exclude_important_subject_keywords"], ["confirmation"])
        self.assertEqual(overrides["force_newsletter_senders"], ["service@vocus.cc"])
        self.assertEqual(overrides["force_newsletter_subject_keywords"], ["最新內容動態"])

    def test_render_page_contains_chinese_explanations(self) -> None:
        raw = {
            "whitelist_senders": ["boss@company.com"],
            "accounts": [{"id": "work", "display_name": "工作信箱", "overrides": {}}],
        }

        html = _render_page(raw)
        self.assertIn("郵件分類規則設定中心", html)
        self.assertIn("規則優先順序", html)
        self.assertIn("工作信箱", html)
        self.assertIn("新增規則", html)


if __name__ == "__main__":
    unittest.main()
