"""Local publish task storage."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from bili_cli.config import APP_DIR, ensure_dirs


TASK_DIR = APP_DIR / "logs" / "publish"


def create_publish_task(plan: dict[str, Any], *, status: str = "planned") -> dict[str, Any]:
    ensure_dirs()
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    task_id = uuid.uuid4().hex[:12]
    task = {
        "task_id": task_id,
        "status": status,
        "created_at": datetime.now().astimezone().isoformat(),
        "updated_at": datetime.now().astimezone().isoformat(),
        "plan": plan,
    }
    _task_path(task_id).write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return task


def load_publish_task(task_id: str) -> dict[str, Any]:
    path = _task_path(task_id)
    if not path.exists():
        from bili_cli.errors import APIError

        raise APIError(f"Publish task not found: {task_id}", "NOT_FOUND")
    return json.loads(path.read_text(encoding="utf-8"))


def list_publish_tasks(limit: int = 20) -> list[dict[str, Any]]:
    ensure_dirs()
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(TASK_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    tasks = []
    for path in files[: max(limit, 0)]:
        try:
            tasks.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return tasks


def update_publish_task(task_id: str, *, status: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
    task = load_publish_task(task_id)
    task["status"] = status
    task["updated_at"] = datetime.now().astimezone().isoformat()
    if result is not None:
        task["result"] = result
    _task_path(task_id).write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    return task


def _task_path(task_id: str) -> Path:
    safe = "".join(ch for ch in task_id if ch.isalnum() or ch in {"-", "_"})
    return TASK_DIR / f"{safe}.json"
