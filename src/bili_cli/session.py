"""Account and session storage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bili_cli.config import ACCOUNTS_PATH, APP_DIR, ensure_dirs, get_value, init_config


def account_name(account: str | None = None) -> str:
    if account:
        return account
    return str(get_value("default.account", "default"))


def cookie_path(account: str | None = None) -> Path:
    return APP_DIR / "cookies" / f"{account_name(account)}.json"


def storage_state_path(account: str | None = None) -> Path:
    return APP_DIR / "storage_state" / f"{account_name(account)}.json"


def has_session(account: str | None = None) -> bool:
    return cookie_path(account).exists() or storage_state_path(account).exists()


def load_cookies(account: str | None = None) -> list[dict[str, Any]]:
    paths = [cookie_path(account), storage_state_path(account)]
    for path in paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("cookies"), list):
            return data["cookies"]
    return []


def cookie_header(account: str | None = None) -> str:
    pairs = []
    for cookie in load_cookies(account):
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value is not None:
            pairs.append(f"{name}={value}")
    return "; ".join(pairs)


def csrf_token(account: str | None = None) -> str:
    for cookie in load_cookies(account):
        if cookie.get("name") == "bili_jct":
            return str(cookie.get("value") or "")
    return ""


def save_cookies(cookies: list[dict[str, Any]], account: str | None = None) -> None:
    ensure_dirs()
    cookie_path(account).write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    add_account(account_name(account))


def save_storage_state(state: dict[str, Any], account: str | None = None) -> None:
    ensure_dirs()
    storage_state_path(account).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    cookies = state.get("cookies")
    if isinstance(cookies, list):
        save_cookies(cookies, account)
    add_account(account_name(account))


def clear_session(account: str | None = None) -> None:
    for path in [cookie_path(account), storage_state_path(account)]:
        if path.exists():
            path.unlink()


def load_accounts() -> dict[str, Any]:
    init_config()
    try:
        data = json.loads(ACCOUNTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {"default": "default", "accounts": ["default"]}
    accounts = data.get("accounts")
    if not isinstance(accounts, list):
        data["accounts"] = ["default"]
    if not data.get("default"):
        data["default"] = "default"
    return data


def save_accounts(data: dict[str, Any]) -> None:
    ensure_dirs()
    ACCOUNTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_accounts() -> list[str]:
    return list(dict.fromkeys(load_accounts().get("accounts", ["default"])))


def add_account(name: str) -> None:
    data = load_accounts()
    accounts = list_accounts()
    if name not in accounts:
        accounts.append(name)
    data["accounts"] = accounts
    if not data.get("default"):
        data["default"] = name
    save_accounts(data)


def remove_account(name: str) -> None:
    data = load_accounts()
    accounts = [item for item in list_accounts() if item != name]
    data["accounts"] = accounts or ["default"]
    if data.get("default") == name:
        data["default"] = data["accounts"][0]
    save_accounts(data)
    clear_session(name)


def set_default_account(name: str) -> None:
    add_account(name)
    data = load_accounts()
    data["default"] = name
    save_accounts(data)


def default_account() -> str:
    return str(load_accounts().get("default", "default"))
