"""Browser handoff helpers for Bilibili creator center."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bili_cli.config import get_value
from bili_cli.errors import APIError
from bili_cli.session import load_cookies, storage_state_path


def open_creator_page(
    url: str,
    *,
    account: str | None = None,
    timeout: int | None = None,
    headless: bool | None = None,
    upload_file: str | None = None,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - optional browser install
        raise APIError("Playwright is not installed or unavailable", "PLAYWRIGHT_UNAVAILABLE", True) from exc

    timeout_seconds = int(timeout if timeout is not None else get_value("browser.timeout", 180))
    browser_headless = bool(headless if headless is not None else get_value("browser.headless", False))
    attached_file = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=browser_headless)
        context_kwargs: dict[str, Any] = {}
        state_path = storage_state_path(account)
        if state_path.exists():
            context_kwargs["storage_state"] = str(state_path)
        context = browser.new_context(**context_kwargs)
        cookies = load_cookies(account)
        if cookies and not state_path.exists():
            context.add_cookies(cookies)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
        if upload_file:
            attached_file = _try_attach_file(page, upload_file)
        print("Creator browser is open. Finish manually if needed, then press Enter here to close it.")
        try:
            input()
        except EOFError:
            page.wait_for_timeout(5000)
        browser.close()

    return {"opened": True, "url": url, "attached_file": attached_file, "manual_required": True}


def _try_attach_file(page: Any, upload_file: str) -> bool:
    path = Path(upload_file).expanduser()
    if not path.exists():
        return False
    try:
        locator = page.locator('input[type="file"]').first
        locator.set_input_files(str(path), timeout=5000)
        return True
    except Exception:
        return False
