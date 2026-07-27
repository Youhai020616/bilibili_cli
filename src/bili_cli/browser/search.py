"""Browser fallback for Bilibili search."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

from bili_cli.errors import APIError, CaptchaRequiredError
from bili_cli.session import storage_state_path

BVID_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


def browser_search(
    keyword: str,
    *,
    account: str | None = None,
    limit: int = 20,
    timeout: int = 120,
    headless: bool = False,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on optional browser install
        raise APIError("Playwright is not installed or unavailable", "PLAYWRIGHT_UNAVAILABLE", True) from exc

    search_url = f"https://search.bilibili.com/video?keyword={quote_plus(keyword)}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context_kwargs: dict[str, Any] = {}
        state_path = storage_state_path(account)
        if state_path.exists():
            context_kwargs["storage_state"] = str(state_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(search_url, wait_until="domcontentloaded")

        deadline_ms = timeout * 1000
        try:
            page.wait_for_selector('a[href*="/video/BV"]', timeout=deadline_ms)
        except Exception as exc:
            browser.close()
            raise CaptchaRequiredError("Browser search did not expose result links; manual verification may be required") from exc

        raw_items = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('a[href*="/video/BV"]')).map((a) => {
              const card = a.closest('[class*="card"], [class*="item"], [class*="video"]') || a.parentElement;
              return {
                title: a.getAttribute('title') || a.innerText || '',
                url: a.href || '',
                text: card ? card.innerText : ''
              };
            })
            """
        )
        browser.close()

    items = []
    seen = set()
    for raw in raw_items:
        match = BVID_RE.search(str(raw.get("url") or ""))
        if not match:
            continue
        bvid = match.group(1)
        if bvid in seen:
            continue
        seen.add(bvid)
        items.append(
            {
                "type": "video",
                "bvid": bvid,
                "title": _clean_title(raw.get("title") or raw.get("text") or ""),
                "url": f"https://www.bilibili.com/video/{bvid}/",
                "strategy": "browser",
            }
        )
        if len(items) >= limit:
            break
    return {"keyword": keyword, "type": "video", "limit": limit, "items": items}


def _clean_title(value: Any) -> str:
    text = str(value or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""
