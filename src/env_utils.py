from __future__ import annotations

import os
import stat
from pathlib import Path

DEFAULT_ENV_FILE = "config/secrets.local.env"


class EnvFilePermissionError(RuntimeError):
    pass


def resolve_env_path(path: str | Path) -> Path:
    return Path(path).expanduser()


def ensure_secure_env_permissions(path: str | Path) -> None:
    env_path = resolve_env_path(path)
    if not env_path.exists() or os.name == "nt":
        return

    mode = stat.S_IMODE(env_path.stat().st_mode)
    if mode != 0o600:
        raise EnvFilePermissionError(
            f"Insecure env file permission: {env_path} mode={oct(mode)}. Please run: chmod 600 {env_path}"
        )


def parse_env_file(path: str | Path) -> dict[str, str]:
    env_path = resolve_env_path(path)
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
    ensure_secure_env_permissions(path)
    loaded = parse_env_file(path)
    for key, value in loaded.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return loaded


def upsert_env_values(path: str | Path, updates: dict[str, str]) -> None:
    env_path = resolve_env_path(path)
    env_path.parent.mkdir(parents=True, exist_ok=True)
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
