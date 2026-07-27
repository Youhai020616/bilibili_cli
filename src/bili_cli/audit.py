"""Audit log helpers for write operations."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from bili_cli.config import APP_DIR, ensure_dirs


def write_audit_event(
    *,
    command: str,
    action: str,
    target: dict[str, Any],
    account: str | None,
    dry_run: bool,
    strategy: str,
    ok: bool,
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> Path:
    ensure_dirs()
    now = datetime.now().astimezone()
    path = APP_DIR / "audit" / f"{now.date().isoformat()}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": now.isoformat(),
        "command": command,
        "action": action,
        "target": target,
        "account": account,
        "dry_run": dry_run,
        "executed": not dry_run,
        "strategy": strategy,
        "ok": ok,
    }
    if result is not None:
        event["result"] = result
    if error is not None:
        event["error"] = error
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path
