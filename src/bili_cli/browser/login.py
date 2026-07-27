"""Playwright login/session helpers."""

from __future__ import annotations

import time
from typing import Any

from bili_cli.config import get_value
from bili_cli.errors import APIError
from bili_cli.session import save_cookies, save_storage_state, storage_state_path


def login_with_browser(*, account: str | None = None, timeout: int | None = None, headless: bool | None = None) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on optional browser install
        raise APIError("Playwright is not installed or unavailable", "PLAYWRIGHT_UNAVAILABLE", True) from exc

    timeout_seconds = int(timeout if timeout is not None else get_value("browser.timeout", 180))
    browser_headless = bool(headless if headless is not None else get_value("browser.headless", False))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=browser_headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.bilibili.com/", wait_until="domcontentloaded")
        start = time.time()
        while time.time() - start < timeout_seconds:
            cookies = context.cookies()
            names = {cookie.get("name") for cookie in cookies}
            if "SESSDATA" in names and "bili_jct" in names:
                state = context.storage_state(path=str(storage_state_path(account)))
                save_storage_state(state, account)
                save_cookies(cookies, account)
                browser.close()
                return {"logged_in": True, "cookies": len(cookies)}
            page.wait_for_timeout(2000)
        state = context.storage_state(path=str(storage_state_path(account)))
        save_storage_state(state, account)
        browser.close()
        return {"logged_in": False, "cookies": len(state.get("cookies") or [])}


def import_cookies_from_browser(*, account: str | None = None, browser_name: str = "chrome") -> dict[str, Any]:
    try:
        import browser_cookie3
    except Exception as exc:  # pragma: no cover - optional OS/keychain behavior
        raise APIError("browser-cookie3 is not installed or unavailable", "BROWSER_COOKIE_UNAVAILABLE", True) from exc

    loader_map = {
        "chrome": "chrome",
        "chromium": "chromium",
        "firefox": "firefox",
        "safari": "safari",
        "edge": "edge",
    }
    loader_name = loader_map.get(browser_name)
    if not loader_name or not hasattr(browser_cookie3, loader_name):
        raise APIError(f"Unsupported browser for cookie import: {browser_name}", "UNSUPPORTED_INPUT")

    try:
        jar = getattr(browser_cookie3, loader_name)(domain_name="bilibili.com")
    except Exception as exc:  # pragma: no cover - browser/keychain dependent
        raise APIError(f"Unable to import cookies from {browser_name}: {exc}", "BROWSER_COOKIE_IMPORT_FAILED", True) from exc

    cookies = []
    for cookie in jar:
        domain = cookie.domain or ".bilibili.com"
        if "bilibili.com" not in domain:
            continue
        cookies.append(
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": domain,
                "path": cookie.path or "/",
                "expires": float(cookie.expires or -1),
                "httpOnly": bool(getattr(cookie, "_rest", {}).get("HttpOnly", False)),
                "secure": bool(cookie.secure),
                "sameSite": "Lax",
            }
        )
    if not cookies:
        raise APIError(f"No Bilibili cookies found in {browser_name}", "COOKIE_NOT_FOUND", True)
    save_cookies(cookies, account)
    return {"imported": True, "browser": browser_name, "cookies": len(cookies)}


def open_browser_session(*, account: str | None = None, headless: bool = False) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        raise APIError("Playwright is not installed or unavailable", "PLAYWRIGHT_UNAVAILABLE", True) from exc

    storage_path = storage_state_path(account)
    with sync_playwright() as p:
        kwargs = {"headless": headless}
        browser = p.chromium.launch(**kwargs)
        context_kwargs: dict[str, Any] = {}
        if storage_path.exists():
            context_kwargs["storage_state"] = str(storage_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto("https://www.bilibili.com/", wait_until="domcontentloaded")
        print("Browser is open. Press Enter here to close it.")
        try:
            input()
        except EOFError:
            page.wait_for_timeout(5000)
        browser.close()
