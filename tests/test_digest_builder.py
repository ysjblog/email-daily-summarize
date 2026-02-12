import unittest

from src.digest_builder import build_combined_digest, build_external_safe_digest, build_line_digest


class DigestBuilderTests(unittest.TestCase):
    def test_build_combined_digest_groups_sections_by_category_then_account(self) -> None:
        work_report = {
            "account_id": "work",
            "display_name": "Work Mail",
            "important": [{"subject": "Work Important", "sender": "w@example.com", "snippet": "w"}],
            "moved": [],
            "spam_suspects": [],
            "newsletters": [{"subject": "Work News", "source": "news@work.com", "bullets": ["w"]}],
        }
        personal_report = {
            "account_id": "personal",
            "display_name": "Personal Mail",
            "important": [{"subject": "Personal Important", "sender": "p@example.com", "snippet": "p"}],
            "moved": [],
            "spam_suspects": [],
            "newsletters": [{"subject": "Personal News", "source": "news@personal.com", "bullets": ["p"]}],
        }

        digest = build_combined_digest("2026-02-12-1300", [work_report, personal_report], [])

        important_section = digest.index("## 1) ⭐ **重要信件**")
        newsletter_section = digest.index("## 2) 📰 **電子報摘要**")
        self.assertLess(important_section, newsletter_section)
        self.assertIn("### 💼 **Work Mail** (`work`) · _1 封_", digest)
        self.assertIn("### 🏠 **Personal Mail** (`personal`) · _1 封_", digest)
        self.assertNotIn("## Account:", digest)

    def test_build_line_digest_renders_all_sections_with_limits(self) -> None:
        account_report = {
            "account_id": "work",
            "display_name": "Work Mail",
            "important": [
                {"subject": f"Important {i}", "sender": f"imp{i}@mail.com", "snippet": f"Important snippet {i}"}
                for i in range(1, 6)
            ],
            "moved": [{"subject": f"Moved {i}", "sender": "moved@mail.com", "reason": "rule"} for i in range(1, 5)],
            "spam_suspects": [{"subject": f"Spam {i}", "sender": "spam@mail.com", "score": 80} for i in range(1, 5)],
            "newsletters": [
                {"subject": f"Newsletter {i}", "source": "news@site.com", "bullets": ["A", "B", "C"]} for i in range(1, 5)
            ],
        }

        digest = build_line_digest("2026-02-12-1300", [account_report], [])

        self.assertIn("【1) ⭐ 重要信件】", digest)
        self.assertIn("【2) 📰 電子報摘要】", digest)
        self.assertIn("【3) 📦 已搬移摘要】", digest)
        self.assertIn("【4) 🚨 疑似垃圾但重要】", digest)
        self.assertIn("＜💼 Work Mail (work)＞ (5/5)", digest)
        self.assertIn("＜💼 Work Mail (work)＞ (3/4)", digest)
        self.assertIn("👤 寄件人: imp5@mail.com", digest)
        self.assertIn("✉️ 主旨: Important 5", digest)
        self.assertIn("📝 摘要: Important snippet 1", digest)
        self.assertIn("🔻 主旨: ~~Moved 1~~", digest)
        self.assertIn("🔴 原因: rule", digest)
        self.assertIn("👤 寄件人: spam@mail.com", digest)
        self.assertIn("⚠️ 主旨: Spam 1", digest)
        self.assertIn("👤 寄件人: news@site.com", digest)
        self.assertIn("✉️ 主旨: Newsletter 1", digest)
        self.assertIn("- ...還有 1 筆", digest)
        self.assertNotIn("(rule)", digest)

    def test_build_line_digest_limits_important_snippet_to_20_chars(self) -> None:
        account_report = {
            "account_id": "work",
            "display_name": "Work Mail",
            "important": [
                {
                    "subject": "Important",
                    "sender": "imp@mail.com",
                    "snippet": "1234567890123456789012345",
                }
            ],
            "moved": [],
            "spam_suspects": [],
            "newsletters": [],
        }

        digest = build_line_digest("2026-02-12-1305", [account_report], [])
        snippet_line = next(line for line in digest.splitlines() if line.strip().startswith("📝 摘要: "))
        rendered = snippet_line.split("📝 摘要: ", 1)[1]

        self.assertEqual(rendered, "12345678901234567...")
        self.assertLessEqual(len(rendered), 20)

    def test_build_combined_digest_hides_important_reason(self) -> None:
        account_report = {
            "account_id": "work",
            "display_name": "Work Mail",
            "important": [{"subject": "Top Secret", "sender": "boss@example.com", "reason": "priority keyword"}],
            "moved": [],
            "spam_suspects": [],
            "newsletters": [],
        }

        digest = build_combined_digest("2026-02-12-1306", [account_report], [])

        self.assertIn("## 1) ⭐ **重要信件**", digest)
        self.assertIn("### 💼 **Work Mail** (`work`) · _1 封_", digest)
        self.assertIn("👤 **寄件人**：`boss@example.com`", digest)
        self.assertIn("✉️ **主旨**：**Top Secret**", digest)
        self.assertNotIn("priority keyword", digest)

    def test_build_line_digest_truncates_to_line_limit(self) -> None:
        long_text = "x" * 1200
        account_report = {
            "account_id": "work",
            "display_name": "Work Mail",
            "important": [{"subject": long_text} for _ in range(10)],
            "moved": [{"subject": long_text, "reason": "rule"} for _ in range(10)],
            "spam_suspects": [{"subject": long_text, "score": 90} for _ in range(10)],
            "newsletters": [
                {"subject": long_text, "source": "newsletter@example.com", "bullets": [long_text, long_text, long_text]}
                for _ in range(10)
            ],
        }

        digest = build_line_digest("2026-02-12-1301", [account_report], [])

        self.assertLessEqual(len(digest), 4900)
        self.assertTrue(digest.endswith("[訊息過長，已截斷]"))

    def test_build_external_safe_digest_redacts_sensitive_fields(self) -> None:
        account_report = {
            "account_id": "work",
            "display_name": "Work Mail",
            "important": [{"subject": "Top Secret", "sender": "boss@example.com", "snippet": "do not leak"}],
            "moved": [{"subject": "Moved Secret", "sender": "x@y.com"}],
            "spam_suspects": [{"subject": "Spam Secret"}],
            "newsletters": [{"subject": "Newsletter Secret"}],
        }
        digest = build_external_safe_digest("2026-02-12-1302", [account_report], [{"account_id": "personal"}])

        self.assertIn("[Email Digest Safe Summary] 2026-02-12-1302", digest)
        self.assertIn("【1) ⭐ 重要信件】", digest)
        self.assertIn("【2) 📰 電子報摘要】", digest)
        self.assertIn("- 總數: 1", digest)
        self.assertIn("- 💼 Work Mail (work): 1", digest)
        self.assertIn("失敗帳號:", digest)
        self.assertIn("- personal", digest)
        self.assertNotIn("Top Secret", digest)
        self.assertNotIn("boss@example.com", digest)
        self.assertNotIn("do not leak", digest)


if __name__ == "__main__":
    unittest.main()
