from __future__ import annotations

from pathlib import Path

from bili_cli import index_cache


def test_save_and_resolve_index(tmp_path: Path, monkeypatch) -> None:
    cache_path = tmp_path / "search_index.json"
    monkeypatch.setattr(index_cache, "CACHE_PATH", cache_path)
    monkeypatch.setattr(index_cache, "CACHE_TTL_SECONDS", 3600)

    index_cache.save_index(
        [{"title": "hello", "bvid": "BV1xx411c7mD", "aid": 2}],
        query="hello",
        item_type="video",
    )

    assert index_cache.resolve_video_ref("1") == "BV1xx411c7mD"
    assert index_cache.resolve_video_ref("BV1xx411c7mD") == "BV1xx411c7mD"
