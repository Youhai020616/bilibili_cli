from __future__ import annotations

from pathlib import Path

from bili_cli.commands.publish import build_publish_plan
from bili_cli.publish_tasks import create_publish_task, load_publish_task


def test_build_publish_plan_validates_files(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"cover")
    plan = build_publish_plan(
        title="Title",
        description="Desc",
        video=str(video),
        cover=str(cover),
        tags=("AI,编程", "B站"),
        tid=123,
        copyright="original",
        source="",
        schedule=None,
    )
    assert plan["title"] == "Title"
    assert plan["video"]["size"] == 5
    assert plan["cover"]["size"] == 5
    assert plan["tags"] == ["AI", "编程", "B站"]


def test_publish_task_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("bili_cli.publish_tasks.TASK_DIR", tmp_path)
    task = create_publish_task({"title": "Title"}, status="planned")
    loaded = load_publish_task(task["task_id"])
    assert loaded["status"] == "planned"
    assert loaded["plan"]["title"] == "Title"
