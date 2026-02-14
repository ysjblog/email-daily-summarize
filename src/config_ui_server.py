from __future__ import annotations

from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import yaml


def run_config_ui_server(config_path: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    path = Path(config_path)
    server = ThreadingHTTPServer((host, port), _build_handler(path))
    print(f"設定介面已啟動：http://{host}:{port}")
    print("按 Ctrl+C 可停止服務。")
    server.serve_forever()


def _build_handler(config_path: Path):
    class ConfigUIHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/":
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            raw = _load_yaml(config_path)
            body = _render_page(raw)
            data = body.encode("utf-8")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/update":
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            size = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(size).decode("utf-8")
            data = parse_qs(payload, keep_blank_values=False)

            action = _pick_value(data, "action")
            value = _pick_value(data, "value")
            account_id = _pick_value(data, "account_id")

            raw = _load_yaml(config_path)
            _apply_action(raw, action, value, account_id)
            _save_yaml(config_path, raw)

            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/")
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    return ConfigUIHandler


def _pick_value(data: dict[str, list[str]], key: str) -> str:
    values = data.get(key) or [""]
    return values[0].strip()


def _apply_action(raw: dict[str, Any], action: str, value: str, account_id: str) -> None:
    if action == "add_global_whitelist":
        _add_unique(raw, "whitelist_senders", value)
        return
    if action == "remove_global_whitelist":
        _remove_value(raw, "whitelist_senders", value)
        return
    if action == "add_global_newsletter":
        _add_unique(raw, "newsletter_sources", value)
        return
    if action == "remove_global_newsletter":
        _remove_value(raw, "newsletter_sources", value)
        return
    if action == "add_account_whitelist":
        _add_account_override(raw, account_id, "whitelist_senders", value)
        return
    if action == "remove_account_whitelist":
        _remove_account_override(raw, account_id, "whitelist_senders", value)
        return
    if action == "add_account_newsletter":
        _add_account_override(raw, account_id, "newsletter_sources", value)
        return
    if action == "remove_account_newsletter":
        _remove_account_override(raw, account_id, "newsletter_sources", value)
        return
    if action == "add_global_exclude_important_sender":
        _add_unique(raw, "exclude_important_senders", value)
        return
    if action == "remove_global_exclude_important_sender":
        _remove_value(raw, "exclude_important_senders", value)
        return
    if action == "add_global_exclude_important_subject":
        _add_unique(raw, "exclude_important_subject_keywords", value)
        return
    if action == "remove_global_exclude_important_subject":
        _remove_value(raw, "exclude_important_subject_keywords", value)
        return
    if action == "add_global_force_newsletter_sender":
        _add_unique(raw, "force_newsletter_senders", value)
        return
    if action == "remove_global_force_newsletter_sender":
        _remove_value(raw, "force_newsletter_senders", value)
        return
    if action == "add_global_force_newsletter_subject":
        _add_unique(raw, "force_newsletter_subject_keywords", value)
        return
    if action == "remove_global_force_newsletter_subject":
        _remove_value(raw, "force_newsletter_subject_keywords", value)
        return
    if action == "add_account_exclude_important_sender":
        _add_account_override(raw, account_id, "exclude_important_senders", value)
        return
    if action == "remove_account_exclude_important_sender":
        _remove_account_override(raw, account_id, "exclude_important_senders", value)
        return
    if action == "add_account_exclude_important_subject":
        _add_account_override(raw, account_id, "exclude_important_subject_keywords", value)
        return
    if action == "remove_account_exclude_important_subject":
        _remove_account_override(raw, account_id, "exclude_important_subject_keywords", value)
        return
    if action == "add_account_force_newsletter_sender":
        _add_account_override(raw, account_id, "force_newsletter_senders", value)
        return
    if action == "remove_account_force_newsletter_sender":
        _remove_account_override(raw, account_id, "force_newsletter_senders", value)
        return
    if action == "add_account_force_newsletter_subject":
        _add_account_override(raw, account_id, "force_newsletter_subject_keywords", value)
        return
    if action == "remove_account_force_newsletter_subject":
        _remove_account_override(raw, account_id, "force_newsletter_subject_keywords", value)
        return


def _add_unique(raw: dict[str, Any], key: str, value: str) -> None:
    value = value.strip()
    if not value:
        return
    items = raw.setdefault(key, [])
    if value not in items:
        items.append(value)


def _remove_value(raw: dict[str, Any], key: str, value: str) -> None:
    items = raw.get(key)
    if not isinstance(items, list):
        return
    raw[key] = [item for item in items if item != value]


def _find_account(raw: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    accounts = raw.get("accounts")
    if not isinstance(accounts, list):
        return None
    for account in accounts:
        if isinstance(account, dict) and str(account.get("id", "")).strip() == account_id:
            return account
    return None


def _add_account_override(raw: dict[str, Any], account_id: str, key: str, value: str) -> None:
    value = value.strip()
    if not account_id or not value:
        return
    account = _find_account(raw, account_id)
    if not account:
        return
    overrides = account.setdefault("overrides", {})
    items = overrides.setdefault(key, [])
    if value not in items:
        items.append(value)


def _remove_account_override(raw: dict[str, Any], account_id: str, key: str, value: str) -> None:
    if not account_id:
        return
    account = _find_account(raw, account_id)
    if not account:
        return
    overrides = account.get("overrides", {})
    items = overrides.get(key)
    if not isinstance(items, list):
        return
    overrides[key] = [item for item in items if item != value]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _save_yaml(path: Path, raw: dict[str, Any]) -> None:
    text = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False)
    path.write_text(text, encoding="utf-8")


def _render_rule_block(
    title: str,
    description: str,
    items: list[str],
    add_action: str,
    remove_action: str,
    placeholder: str,
    account_id: str | None = None,
) -> list[str]:
    # Use different colors for different types of cards to help visual distinction
    card_type = "neutral"
    if "排除" in title or "黑名單" in title:
        card_type = "danger"
    elif "白名單" in title or "電子報" in title:
        card_type = "success"

    rows = [
        f"<section class='rule-card {card_type}'>",
        f"<div class='card-header'><h3>{escape(title)}</h3></div>",
        f"<p class='hint'>{escape(description)}</p>",
        "<div class='chip-container'>",
    ]
    
    if items:
        for item in items:
            rows.append(f"<div class='chip'><span>{escape(item)}</span>")
            rows.append('<form method="post" action="/update" class="inline-form">')
            rows.append(f'<input type="hidden" name="action" value="{escape(remove_action)}">')
            rows.append(f'<input type="hidden" name="value" value="{escape(item)}">')
            if account_id:
                rows.append(f'<input type="hidden" name="account_id" value="{escape(account_id)}">')
            rows.append('<button type="submit" class="icon-btn" title="移除">×</button>')
            rows.append("</form></div>")
    else:
        rows.append("<div class='empty-state'>目前沒有規則</div>")
        
    rows.append("</div>") # End chip-container
    
    rows.append('<form method="post" action="/update" class="add-form">')
    rows.append(f'<input type="hidden" name="action" value="{escape(add_action)}">')
    if account_id:
        rows.append(f'<input type="hidden" name="account_id" value="{escape(account_id)}">')
    rows.append(f'<div class="input-group"><input name="value" required placeholder="{escape(placeholder)}">')
    rows.append('<button type="submit" class="add-btn">＋ 新增</button></div>')
    rows.append("</form></section>")
    return rows


def _render_page(raw: dict[str, Any]) -> str:
    whitelist = _list_value(raw, "whitelist_senders")
    newsletters = _list_value(raw, "newsletter_sources")
    exclude_senders = _list_value(raw, "exclude_important_senders")
    exclude_subjects = _list_value(raw, "exclude_important_subject_keywords")
    force_newsletter_senders = _list_value(raw, "force_newsletter_senders")
    force_newsletter_subjects = _list_value(raw, "force_newsletter_subject_keywords")
    accounts = raw.get("accounts") if isinstance(raw.get("accounts"), list) else []

    lines = [
        "<!doctype html>",
        "<html lang='zh-TW'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>Daily Summarize 設定中心</title>",
        "<link rel='preconnect' href='https://fonts.googleapis.com'>",
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>",
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700&display=swap' rel='stylesheet'>",
        "<style>",
        ":root {",
        "  --primary: #2563eb; --primary-hover: #1d4ed8; --bg: #f8fafc; --surface: #ffffff;",
        "  --text: #0f172a; --text-muted: #64748b; --border: #e2e8f0;",
        "  --danger: #ef4444; --danger-bg: #fef2f2; --danger-text: #991b1b;",
        "  --success: #10b981; --success-bg: #ecfdf5; --success-text: #065f46;",
        "  --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);",
        "  --radius: 12px;",
        "}",
        "body { margin: 0; font-family: 'Inter', 'Noto Sans TC', sans-serif; background-color: var(--bg); color: var(--text); line-height: 1.5; -webkit-font-smoothing: antialiased; }",
        ".container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }",
        ".header { text-align: center; margin-bottom: 48px; }",
        "h1 { font-size: 32px; font-weight: 700; margin: 0 0 12px 0; letter-spacing: -0.02em; }",
        ".subtitle { color: var(--text-muted); font-size: 16px; max-width: 600px; margin: 0 auto; }",
        "h2 { font-size: 20px; font-weight: 600; margin: 32px 0 16px; display: flex; align-items: center; gap: 8px; color: var(--text); }",
        "h2::after { content: ''; flex: 1; height: 1px; background: var(--border); margin-left: 16px; }",
        
        "/* Grid Layout */",
        ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 24px; }",
        
        "/* Card Styles */",
        ".rule-card { background: var(--surface); border-radius: var(--radius); border: 1px solid var(--border); padding: 24px; box-shadow: var(--shadow); transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; }",
        ".rule-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -1px rgb(0 0 0 / 0.06); }",
        ".rule-card.danger { border-top: 4px solid var(--danger); }",
        ".rule-card.success { border-top: 4px solid var(--success); }",
        ".rule-card.neutral { border-top: 4px solid var(--primary); }",
        
        ".card-header h3 { margin: 0 0 8px 0; font-size: 16px; font-weight: 600; }",
        ".hint { font-size: 13px; color: var(--text-muted); margin: 0 0 16px 0; min-height: 40px; }",
        
        "/* Chips */",
        ".chip-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; flex: 1; }",
        ".chip { display: inline-flex; align-items: center; background: #f1f5f9; padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 500; color: var(--text); border: 1px solid transparent; }",
        ".rule-card.danger .chip { background: var(--danger-bg); color: var(--danger-text); }",
        ".rule-card.success .chip { background: var(--success-bg); color: var(--success-text); }",
        ".chip span { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }",
        
        "/* Buttons */",
        ".icon-btn { background: none; border: none; font-size: 16px; color: currentColor; cursor: pointer; padding: 0 0 0 6px; opacity: 0.6; display: flex; align-items: center; }",
        ".icon-btn:hover { opacity: 1; }",
        ".add-btn { background: var(--primary); color: white; border: none; padding: 0 16px; border-radius: 8px; font-weight: 500; cursor: pointer; transition: background 0.2s; white-space: nowrap; }",
        ".add-btn:hover { background: var(--primary-hover); }",
        
        "/* Forms */",
        ".inline-form { margin: 0; padding: 0; display: inline-flex; }",
        ".add-form { margin-top: auto; }",
        ".input-group { display: flex; gap: 8px; }",
        "input { flex: 1; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; transition: border-color 0.2s; width: 100%; box-sizing: border-box; }",
        "input:focus { outline: none; border-color: var(--primary); ring: 2px solid var(--primary-bg); }",
        
        ".empty-state { color: var(--text-muted); font-size: 13px; font-style: italic; padding: 12px 0; }",
        
        "/* Account Section */",
        ".account-section { background: white; border-radius: var(--radius); border: 1px dashed var(--border); padding: 32px; margin-top: 40px; }",
        ".account-title { font-size: 24px; font-weight: 700; margin-bottom: 24px; display: flex; align-items: baseline; gap: 12px; }",
        ".account-id { font-size: 14px; font-weight: 500; font-family: monospace; background: #e2e8f0; padding: 4px 8px; border-radius: 6px; color: var(--text-muted); }",

        "@media (max-width: 640px) { .grid { grid-template-columns: 1fr; } input { min-width: 0; } }",
        "</style></head><body><div class='container'>",
        
        "<header class='header'>",
        "<h1>Daily Summarize 設定中心</h1>",
        "<div class='subtitle'>",
        "在此設定郵件分類規則。所有變更即時寫入 <code>config/settings.yaml</code>。<br>",
        "建議在正式執行前，先使用 <code>dry-run</code> 模式驗證規則效果。",
        "</div>",
        "</header>",

        "<h2>全域規則 (Global Rules)</h2>",
        "<div class='grid'>",
    ]
    
    # Global Rules
    lines.extend(
        _render_rule_block(
            title="重要信件白名單",
            description="來自這些寄件者的信件將被優先標記為重要。支援完整 Email 或 @domain。",
            items=whitelist,
            add_action="add_global_whitelist",
            remove_action="remove_global_whitelist",
            placeholder="例如: boss@company.com",
        )
    )
    lines.extend(
        _render_rule_block(
            title="電子報來源",
            description="來自這些寄件者的信件將被視為電子報。",
            items=newsletters,
            add_action="add_global_newsletter",
            remove_action="remove_global_newsletter",
            placeholder="例如: newsletter@substack.com",
        )
    )
    lines.extend(
        _render_rule_block(
            title="排外黑名單 (寄件者)",
            description="來自這些寄件者的信件絕不會被標記為重要。",
            items=exclude_senders,
            add_action="add_global_exclude_important_sender",
            remove_action="remove_global_exclude_important_sender",
            placeholder="例如: marketing@spam.com",
        )
    )
    lines.extend(
        _render_rule_block(
            title="排外黑名單 (關鍵字)",
            description="標題包含這些關鍵字的信件絕不會被標記為重要。",
            items=exclude_subjects,
            add_action="add_global_exclude_important_subject",
            remove_action="remove_global_exclude_important_subject",
            placeholder="例如: unsubscribe",
        )
    )
    lines.extend(
        _render_rule_block(
            title="強制電子報 (寄件者)",
            description="來自這些寄件者的信件將強制歸類為電子報，並建立子標籤。",
            items=force_newsletter_senders,
            add_action="add_global_force_newsletter_sender",
            remove_action="remove_global_force_newsletter_sender",
            placeholder="例如: service@vocus.cc",
        )
    )
    lines.extend(
        _render_rule_block(
            title="強制電子報 (關鍵字)",
            description="標題包含這些關鍵字的信件將強制歸類為電子報。",
            items=force_newsletter_subjects,
            add_action="add_global_force_newsletter_subject",
            remove_action="remove_global_force_newsletter_subject",
            placeholder="例如: Weekly Digest",
        )
    )
    lines.append("</div>")

    # Account Specific Rules
    if accounts:
        lines.append("<h2>帳號專屬規則 (Account Overrides)</h2>")
        for account in accounts:
            if not isinstance(account, dict):
                continue
            account_id = str(account.get("id", "")).strip()
            if not account_id:
                continue
            display_name = str(account.get("display_name") or account_id)
            overrides = account.get("overrides", {})
            if not isinstance(overrides, dict):
                overrides = {}

            lines.extend([
                "<div class='account-section'>",
                f"<div class='account-title'>{escape(display_name)} <span class='account-id'>{escape(account_id)}</span></div>",
                "<div class='grid'>"
            ])

            # Render account-specific blocks...
            lines.extend(_render_rule_block(
                title="白名單 (覆寫)",
                description=f"僅適用於 {display_name}，覆蓋全域設定。",
                items=_list_value(overrides, "whitelist_senders"),
                add_action="add_account_whitelist",
                remove_action="remove_account_whitelist",
                placeholder="例如: client@work.com",
                account_id=account_id,
            ))
            
            lines.extend(_render_rule_block(
                title="電子報來源 (覆寫)",
                description=f"僅適用於 {display_name}，覆蓋全域設定。",
                items=_list_value(overrides, "newsletter_sources"),
                add_action="add_account_newsletter",
                remove_action="remove_account_newsletter",
                placeholder="例如: internal-news@work.com",
                account_id=account_id,
            ))

            # Add other overrides similarly if needed, keeping it concise or full based on usage.
            # For brevity in this overhaul, I'll include the main ones user likely needs.
            # Let's include Force Newsletter as that's a key feature now.
            
            lines.extend(_render_rule_block(
                title="強制電子報 (寄件者覆寫)",
                description=f"僅適用於 {display_name}。",
                items=_list_value(overrides, "force_newsletter_senders"),
                add_action="add_account_force_newsletter_sender",
                remove_action="remove_account_force_newsletter_sender",
                placeholder="例如: alerts@monitoring.com",
                account_id=account_id,
            ))

            lines.append("</div></div>") # End grid and account-section

    lines.append("</div></body></html>") # End container
    return "\n".join(lines)


def _list_value(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if isinstance(value, list):
        return value
    return []
