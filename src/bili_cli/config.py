"""Config file management."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_DIR = Path.home() / ".bili"
CONFIG_PATH = APP_DIR / "config.json"
ACCOUNTS_PATH = APP_DIR / "accounts.json"

DIRS = [
    APP_DIR,
    APP_DIR / "cookies",
    APP_DIR / "storage_state",
    APP_DIR / "cache",
    APP_DIR / "downloads",
    APP_DIR / "logs",
    APP_DIR / "audit",
    APP_DIR / "fixtures",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "timeout": 30,
        "retries": 3,
        "proxy": "",
    },
    "browser": {
        "headless": False,
        "timeout": 180,
    },
    "default": {
        "account": "default",
        "download_dir": str(APP_DIR / "downloads"),
        "json": False,
    },
    "rate_limit": {
        "request_delay": 0.5,
    },
}


def ensure_dirs() -> None:
    for directory in DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def init_config(force: bool = False) -> None:
    ensure_dirs()
    if force or not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
    if force or not ACCOUNTS_PATH.exists():
        ACCOUNTS_PATH.write_text(json.dumps({"default": "default", "accounts": ["default"]}, indent=2), encoding="utf-8")


def load_config() -> dict[str, Any]:
    ensure_dirs()
    if not CONFIG_PATH.exists():
        init_config()
    try:
        loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        loaded = {}
    config = deepcopy(DEFAULT_CONFIG)
    _deep_update(config, loaded)
    return config


def save_config(config: dict[str, Any]) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def get_value(path: str, default: Any = None) -> Any:
    current: Any = load_config()
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def set_value(path: str, value: Any) -> None:
    config = load_config()
    current = config
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = _coerce_value(value)
    save_config(config)


def reset_config() -> None:
    save_config(DEFAULT_CONFIG)


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
