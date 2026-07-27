"""Short-index cache for search results."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from bili_cli.config import APP_DIR, ensure_dirs

CACHE_PATH = APP_DIR / "cache" / "search_index.json"
CACHE_TTL_SECONDS = 24 * 60 * 60


def save_index(items: list[dict[str, Any]], *, query: str = "", item_type: str = "video") -> None:
    ensure_dirs()
    entries = []
    for idx, item in enumerate(items, 1):
        entries.append(
            {
                "index": idx,
                "item_type": item.get("type") or item_type,
                "title": item.get("title") or item.get("name") or "",
                "bvid": item.get("bvid") or "",
                "aid": item.get("aid") or "",
                "cid": item.get("cid") or "",
                "mid": item.get("mid") or "",
                "url": item.get("url") or item.get("arcurl") or "",
            }
        )
    payload = {"query": query, "created_at": int(time.time()), "items": entries}
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {"items": []}
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": []}
    created_at = int(payload.get("created_at") or 0)
    if created_at and time.time() - created_at > CACHE_TTL_SECONDS:
        return {"items": [], "expired": True}
    return payload


def resolve_index(value: str) -> dict[str, Any] | None:
    if not value.isdigit():
        return None
    index = int(value)
    if index <= 0:
        return None
    for item in load_index().get("items", []):
        if item.get("index") == index:
            return item
    return None


def resolve_video_ref(value: str) -> str:
    item = resolve_index(value)
    if item:
        return str(item.get("bvid") or item.get("aid") or value)
    return value
