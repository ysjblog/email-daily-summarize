from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


class ConfigError(RuntimeError):
    pass


@dataclass(slots=True)
class AccountSettings:
    id: str
    display_name: str
    env_prefix: str
    enabled: bool = True
    digest_to: str | None = None
    overrides: dict[str, Any] | None = None


class Settings:
    def __init__(self, raw: dict[str, Any]):
        self.raw = deepcopy(raw)
        self.timezone: str = raw.get("timezone", "Asia/Taipei")
        self.run_times: list[str] = raw.get("run_times", ["09:00", "21:00"])
        self.move_mode: str = raw.get("move_mode", "moderate")
        self.labels: dict[str, str] = raw.get("labels", {})
        self.whitelist_senders: list[str] = raw.get("whitelist_senders", [])
        self.priority_keywords: list[str] = raw.get("priority_keywords", [])
        self.newsletter_sources: list[str] = raw.get("newsletter_sources", [])
        self.exclude_important_senders: list[str] = raw.get("exclude_important_senders", [])
        self.exclude_important_subject_keywords: list[str] = raw.get("exclude_important_subject_keywords", [])
        self.force_newsletter_senders: list[str] = raw.get("force_newsletter_senders", [])
        self.force_newsletter_subject_keywords: list[str] = raw.get("force_newsletter_subject_keywords", [])
        self.spam_scan: dict[str, Any] = raw.get("spam_scan", {"enabled": True, "action": "report_only"})
        self.digest: dict[str, Any] = raw.get("digest", {})
        self.digest_redaction_mode: str = _validate_redaction_mode(self.digest.get("redaction_mode", "strict"))
        self.digest["redaction_mode"] = self.digest_redaction_mode
        self.accounts: list[AccountSettings] = self._load_accounts(raw)

    @property
    def archive_label(self) -> str:
        return self.labels.get("archive_label", "Auto/LowPriority")

    @property
    def review_label(self) -> str:
        return self.labels.get("review_label", "Auto/Review")

    @property
    def newsletter_label(self) -> str:
        return self.labels.get("newsletter_label", "Auto/Newsletter")

    def enabled_accounts(self) -> list[AccountSettings]:
        return [acc for acc in self.accounts if acc.enabled]

    def find_account(self, account_id: str) -> AccountSettings:
        for account in self.accounts:
            if account.id == account_id:
                return account
        raise ConfigError(f"Unknown account id: {account_id}")

    def for_account(self, account: AccountSettings) -> "Settings":
        merged = deepcopy(self.raw)
        merged.pop("accounts", None)

        if account.overrides:
            merged = _deep_merge(merged, account.overrides)

        if account.digest_to:
            merged.setdefault("digest", {})
            merged["digest"].setdefault("gmail", {})
            merged["digest"]["gmail"]["to"] = account.digest_to

        return Settings(merged)

    def _load_accounts(self, raw: dict[str, Any]) -> list[AccountSettings]:
        entries = raw.get("accounts")
        if not entries:
            # Backward compatibility for previous single-account config.
            return [
                AccountSettings(
                    id="default",
                    display_name="Default",
                    env_prefix="DEFAULT",
                    enabled=True,
                    digest_to=raw.get("digest", {}).get("gmail", {}).get("to"),
                    overrides={},
                )
            ]

        if not isinstance(entries, list):
            raise ConfigError("accounts must be a list")

        accounts: list[AccountSettings] = []
        for idx, item in enumerate(entries):
            if not isinstance(item, dict):
                raise ConfigError(f"accounts[{idx}] must be a mapping")

            account_id = str(item.get("id", "")).strip()
            env_prefix = str(item.get("env_prefix", "")).strip()
            display_name = str(item.get("display_name", account_id or f"Account-{idx+1}")).strip()

            if not account_id:
                raise ConfigError(f"accounts[{idx}].id is required")
            if not env_prefix:
                raise ConfigError(f"accounts[{idx}].env_prefix is required")

            accounts.append(
                AccountSettings(
                    id=account_id,
                    display_name=display_name,
                    env_prefix=env_prefix,
                    enabled=bool(item.get("enabled", True)),
                    digest_to=item.get("digest_to"),
                    overrides=item.get("overrides") or {},
                )
            )

        return accounts


def load_settings(path: str | Path) -> Settings:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise ConfigError(f"settings file not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as f:
        content = f.read()

    try:
        import yaml  # type: ignore

        raw = yaml.safe_load(content) or {}
    except ModuleNotFoundError:
        raw = _mini_yaml_load(content)

    if not isinstance(raw, dict):
        raise ConfigError("settings must be a mapping")

    return Settings(raw)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _validate_redaction_mode(value: Any) -> str:
    mode = str(value).strip().lower()
    if mode not in {"strict", "balanced", "none"}:
        raise ConfigError("digest.redaction_mode must be one of: strict, balanced, none")
    return mode


def _mini_yaml_load(content: str) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))

    if not lines:
        return {}

    value, index = _parse_node(lines, 0, lines[0][0])
    if index != len(lines):
        raise ConfigError("Unable to parse full yaml content")
    if not isinstance(value, dict):
        raise ConfigError("Top-level yaml content must be mapping")
    return value


def _parse_node(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index

    _, text = lines[index]
    if text.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    obj: dict[str, Any] = {}
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ConfigError(f"Unexpected indent near: {text}")
        if text.startswith("- "):
            break
        if ":" not in text:
            raise ConfigError(f"Invalid YAML line: {text}")

        key, raw_value = text.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        index += 1

        if raw_value != "":
            obj[key] = _parse_scalar(raw_value)
            continue

        if index >= len(lines) or lines[index][0] <= current_indent:
            obj[key] = {}
            continue

        child_indent = lines[index][0]
        child, index = _parse_node(lines, index, child_indent)
        obj[key] = child

    return obj, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ConfigError(f"Unexpected indent near list item: {text}")
        if not text.startswith("- "):
            break

        raw_item = text[2:].strip()
        index += 1

        if raw_item == "":
            if index < len(lines) and lines[index][0] > current_indent:
                child_indent = lines[index][0]
                child, index = _parse_node(lines, index, child_indent)
                items.append(child)
            else:
                items.append(None)
            continue

        is_mapping_item = (
            not raw_item.startswith(("'", '"'))
            and re.match(r"^[^:]+:\s*.*$", raw_item) is not None
        )
        if is_mapping_item:
            synthetic: list[tuple[int, str]] = [(current_indent + 2, raw_item)]
            while index < len(lines) and lines[index][0] > current_indent:
                synthetic.append(lines[index])
                index += 1
            parsed, consumed = _parse_node(synthetic, 0, current_indent + 2)
            if consumed != len(synthetic):
                raise ConfigError("Unable to parse list item mapping")
            items.append(parsed)
            continue

        items.append(_parse_scalar(raw_item))

    return items, index


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip("'").strip('"')
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None
    if value.isdigit():
        return int(value)
    return value
