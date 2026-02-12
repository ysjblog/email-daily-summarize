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
    rows = [f"<section class='rule-card'><h3>{escape(title)}</h3>", f"<p class='hint'>{escape(description)}</p>", "<ul>"]
    if items:
        for item in items:
            rows.append("<li>")
            rows.append(f"<code>{escape(item)}</code>")
            rows.append('<form method="post" action="/update" class="inline-form">')
            rows.append(f'<input type="hidden" name="action" value="{escape(remove_action)}">')
            rows.append(f'<input type="hidden" name="value" value="{escape(item)}">')
            if account_id:
                rows.append(f'<input type="hidden" name="account_id" value="{escape(account_id)}">')
            rows.append('<button type="submit" class="danger">移除</button>')
            rows.append("</form>")
            rows.append("</li>")
    else:
        rows.append("<li><em>目前沒有規則</em></li>")
    rows.append("</ul>")
    rows.append('<form method="post" action="/update" class="add-form">')
    rows.append(f'<input type="hidden" name="action" value="{escape(add_action)}">')
    if account_id:
        rows.append(f'<input type="hidden" name="account_id" value="{escape(account_id)}">')
    rows.append(f'<input name="value" required placeholder="{escape(placeholder)}">')
    rows.append('<button type="submit">新增規則</button>')
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
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>分類規則設定中心</title>",
        "<style>"
        ":root{--bg:#f4f7f1;--ink:#1f2a1f;--muted:#4f5d4f;--card:#ffffff;--line:#d8dfd3;--accent:#2f7a53;--danger:#b83c3c;}"
        "body{margin:0;font-family:'Noto Sans TC','PingFang TC','Microsoft JhengHei',sans-serif;background:linear-gradient(160deg,#f4f7f1,#e9efe4);color:var(--ink);}"
        ".container{max-width:1100px;margin:0 auto;padding:28px 18px 48px;}"
        ".hero{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 22px;box-shadow:0 6px 20px rgba(35,62,38,.08);}"
        "h1{margin:0 0 10px;font-size:28px;}h2{margin:26px 0 12px;font-size:22px;}h3{margin:0 0 8px;font-size:18px;}"
        "p{margin:0 0 10px;line-height:1.6;color:var(--muted);}code{background:#edf3eb;border-radius:6px;padding:2px 6px;}"
        ".tips{margin:14px 0 0;padding-left:20px;}.tips li{margin:6px 0;color:var(--muted);}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:14px;}"
        ".rule-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 14px 12px;}"
        ".hint{font-size:14px;color:var(--muted);min-height:36px;}"
        "ul{margin:10px 0 12px;padding-left:18px;}li{margin:8px 0;}"
        ".inline-form{display:inline;margin-left:10px;}"
        ".add-form{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}"
        "input{border:1px solid #c5d2c3;border-radius:8px;padding:8px 10px;min-width:240px;}"
        "button{border:0;background:var(--accent);color:#fff;border-radius:8px;padding:8px 12px;cursor:pointer;font-weight:600;}"
        "button.danger{background:var(--danger);padding:6px 10px;font-size:13px;}"
        ".account{margin-top:20px;background:rgba(255,255,255,.65);border:1px dashed #cbd6c8;border-radius:14px;padding:14px;}"
        ".account-head{margin-bottom:8px;}"
        "@media (max-width:640px){h1{font-size:24px}.container{padding:20px 12px 28px}}"
        "</style></head><body><div class='container'>",
        "<section class='hero'>",
        "<h1>郵件分類規則設定中心</h1>",
        "<p>這個頁面會直接更新 <code>config/settings.yaml</code>，儲存後下次執行會立即生效。</p>",
        "<p><strong>規則優先順序：</strong>「排除重要」與「強制電子報」會先判斷，再套用白名單、關鍵字與其他分類邏輯。</p>",
        "<ol class='tips'>",
        "<li>想把某類信件從重要信件拿掉（黑名單效果），請加到「排除重要」。</li>",
        "<li>想把某類信件固定歸到電子報，請加到「強制電子報」。</li>",
        "<li>建議先用 <code>dry-run --hours 24</code> 檢查結果，再做正式 <code>run</code>。</li>",
        "</ol>",
        "</section>",
        "<h2>全域規則（套用所有帳號）</h2>",
        "<div class='grid'>",
    ]
    lines.extend(
        _render_rule_block(
            title="重要信件白名單（保留在重要）",
            description="符合寄件者規則的信件會傾向保留在重要。可填完整 email 或 @網域。",
            items=whitelist,
            add_action="add_global_whitelist",
            remove_action="remove_global_whitelist",
            placeholder="例如：boss@company.com 或 @important-client.com",
        )
    )
    lines.extend(
        _render_rule_block(
            title="電子報來源（優先歸類電子報）",
            description="指定寄件者屬於電子報來源，會傾向不列為重要信件。",
            items=newsletters,
            add_action="add_global_newsletter",
            remove_action="remove_global_newsletter",
            placeholder="例如：newsletter@site.com 或 @substack.com",
        )
    )
    lines.extend(
        _render_rule_block(
            title="黑名單（排除重要）：寄件者",
            description="符合寄件者規則的信件，會直接排除在重要信件之外（視為黑名單）。",
            items=exclude_senders,
            add_action="add_global_exclude_important_sender",
            remove_action="remove_global_exclude_important_sender",
            placeholder="例如：campaigns@m.brevo.com 或 @brevo.com",
        )
    )
    lines.extend(
        _render_rule_block(
            title="黑名單（排除重要）：主旨關鍵字",
            description="主旨或摘要包含這些字詞時，會直接排除在重要信件之外（視為黑名單）。",
            items=exclude_subjects,
            add_action="add_global_exclude_important_subject",
            remove_action="remove_global_exclude_important_subject",
            placeholder="例如：campaign has been sent",
        )
    )
    lines.extend(
        _render_rule_block(
            title="強制電子報：寄件者",
            description="符合寄件者規則時，會直接歸類為電子報流程。",
            items=force_newsletter_senders,
            add_action="add_global_force_newsletter_sender",
            remove_action="remove_global_force_newsletter_sender",
            placeholder="例如：service@vocus.cc 或 @vocus.cc",
        )
    )
    lines.extend(
        _render_rule_block(
            title="強制電子報：主旨關鍵字",
            description="主旨或摘要包含這些字詞時，會直接歸類為電子報流程。",
            items=force_newsletter_subjects,
            add_action="add_global_force_newsletter_subject",
            remove_action="remove_global_force_newsletter_subject",
            placeholder="例如：最新內容動態",
        )
    )
    lines.append("</div>")

    lines.append("<h2>帳號專屬規則（只影響單一帳號）</h2>")
    if not accounts:
        lines.append("<p>目前沒有帳號資料可顯示。</p>")
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
        account_whitelist = _list_value(overrides, "whitelist_senders")
        account_newsletters = _list_value(overrides, "newsletter_sources")
        account_exclude_senders = _list_value(overrides, "exclude_important_senders")
        account_exclude_subjects = _list_value(overrides, "exclude_important_subject_keywords")
        account_force_newsletter_senders = _list_value(overrides, "force_newsletter_senders")
        account_force_newsletter_subjects = _list_value(overrides, "force_newsletter_subject_keywords")

        lines.extend(
            [
                "<section class='account'>",
                f"<div class='account-head'><h3>{escape(display_name)} <small><code>{escape(account_id)}</code></small></h3></div>",
                "<div class='grid'>",
            ]
        )
        lines.extend(
            _render_rule_block(
                title="重要信件白名單（帳號覆寫）",
                description="只對這個帳號生效。設定後會覆蓋全域白名單清單。",
                items=account_whitelist,
                add_action="add_account_whitelist",
                remove_action="remove_account_whitelist",
                placeholder="例如：ceo@company.com",
                account_id=account_id,
            )
        )
        lines.extend(
            _render_rule_block(
                title="電子報來源（帳號覆寫）",
                description="只對這個帳號生效。設定後會覆蓋全域電子報來源清單。",
                items=account_newsletters,
                add_action="add_account_newsletter",
                remove_action="remove_account_newsletter",
                placeholder="例如：newsletter@substack.com",
                account_id=account_id,
            )
        )
        lines.extend(
            _render_rule_block(
                title="黑名單（排除重要）：寄件者（帳號覆寫）",
                description="只對這個帳號生效，符合時直接排除在重要信件外（黑名單）。",
                items=account_exclude_senders,
                add_action="add_account_exclude_important_sender",
                remove_action="remove_account_exclude_important_sender",
                placeholder="例如：campaigns@m.brevo.com",
                account_id=account_id,
            )
        )
        lines.extend(
            _render_rule_block(
                title="黑名單（排除重要）：主旨關鍵字（帳號覆寫）",
                description="只對這個帳號生效，主旨/摘要命中時直接排除重要（黑名單）。",
                items=account_exclude_subjects,
                add_action="add_account_exclude_important_subject",
                remove_action="remove_account_exclude_important_subject",
                placeholder="例如：confirmation",
                account_id=account_id,
            )
        )
        lines.extend(
            _render_rule_block(
                title="強制電子報：寄件者（帳號覆寫）",
                description="只對這個帳號生效，符合時直接歸類到電子報。",
                items=account_force_newsletter_senders,
                add_action="add_account_force_newsletter_sender",
                remove_action="remove_account_force_newsletter_sender",
                placeholder="例如：service@vocus.cc",
                account_id=account_id,
            )
        )
        lines.extend(
            _render_rule_block(
                title="強制電子報：主旨關鍵字（帳號覆寫）",
                description="只對這個帳號生效，主旨/摘要命中時直接歸類到電子報。",
                items=account_force_newsletter_subjects,
                add_action="add_account_force_newsletter_subject",
                remove_action="remove_account_force_newsletter_subject",
                placeholder="例如：最新內容動態",
                account_id=account_id,
            )
        )
        lines.extend(["</div>", "</section>"])

    lines.extend(["</div>", "</body></html>"])
    return "\n".join(lines)


def _list_value(raw: dict[str, Any], key: str) -> list[str]:
    value = raw.get(key)
    if isinstance(value, list):
        return value
    return []
