"""Browser fallback for Bilibili ranking."""

from __future__ import annotations

from typing import Any

from bili_cli.api.client import _normalize_video_card
from bili_cli.errors import APIError, CaptchaRequiredError, map_api_code
from bili_cli.session import storage_state_path


def browser_ranking(
    *,
    rid: int = 0,
    account: str | None = None,
    limit: int = 20,
    timeout: int = 120,
    headless: bool = True,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on optional browser install
        raise APIError("Playwright is not installed or unavailable", "PLAYWRIGHT_UNAVAILABLE", True) from exc

    rank_url = "https://www.bilibili.com/v/popular/rank/all/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context_kwargs: dict[str, Any] = {}
        state_path = storage_state_path(account)
        if state_path.exists():
            context_kwargs["storage_state"] = str(state_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(rank_url, wait_until="domcontentloaded", timeout=timeout * 1000)

        try:
            payload = page.evaluate(
                """
                async ({rid}) => {
                  const url = `https://api.bilibili.com/x/web-interface/ranking/v2?rid=${rid}&type=all`;
                  const res = await fetch(url, {
                    credentials: 'include',
                    headers: {
                      'Accept': 'application/json, text/plain, */*',
                      'Referer': 'https://www.bilibili.com/v/popular/rank/all/',
                      'Origin': 'https://www.bilibili.com'
                    }
                  });
                  return await res.json();
                }
                """,
                {"rid": rid},
            )
        except Exception as exc:
            browser.close()
            raise CaptchaRequiredError("Browser ranking fetch failed; manual verification may be required") from exc
        browser.close()

    if isinstance(payload, dict) and payload.get("code", 0) != 0:
        api_code = int(payload.get("code") or 0)
        message = str(payload.get("message") or payload.get("msg") or "")
        raise map_api_code(api_code, message)
    data = payload.get("data") or {}
    raw_items = data.get("list") or []
    return {
        "source": "ranking",
        "rid": rid,
        "items": [_normalize_video_card(item) for item in list(raw_items)[:limit]],
    }
