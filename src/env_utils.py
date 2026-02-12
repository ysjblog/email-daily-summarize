from __future__ import annotations

import os
from pathlib import Path


def parse_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    result: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def load_env_into_os(path: str | Path = ".env", override: bool = False) -> dict[str, str]:
    loaded = parse_env_file(path)
    for key, value in loaded.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return loaded


def upsert_env_values(path: str | Path, updates: dict[str, str]) -> None:
    env_path = Path(path)
    existing_lines: list[str] = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

    handled = set()
    new_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue

        key, _ = line.split("=", 1)
        key = key.strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            handled.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in handled:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
