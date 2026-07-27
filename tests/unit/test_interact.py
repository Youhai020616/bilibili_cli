from __future__ import annotations

import json

import bili_cli.audit as audit
from bili_cli.commands.interact import _write_action


def _audit_events(tmp_path):
    files = list((tmp_path / "audit").glob("*.jsonl"))
    assert len(files) == 1
    return [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]


def test_write_action_defaults_to_dry_run(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(audit, "APP_DIR", tmp_path)
    called = False

    def execute(_client):
        nonlocal called
        called = True
        return {"action": "like"}

    _write_action(
        command="like",
        action="like",
        target={"bvid": "BV1xx411c7mD"},
        account="default",
        dry_run=False,
        yes=False,
        as_json=True,
        execute=execute,
    )

    assert called is False
    event = _audit_events(tmp_path)[0]
    assert event["dry_run"] is True
    assert event["executed"] is False


def test_write_action_executes_with_yes(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(audit, "APP_DIR", tmp_path)
    called = False

    def execute(_client):
        nonlocal called
        called = True
        return {"action": "follow", "mid": "2"}

    _write_action(
        command="follow",
        action="follow",
        target={"mid": "2"},
        account="default",
        dry_run=False,
        yes=True,
        as_json=True,
        execute=execute,
    )

    assert called is True
    event = _audit_events(tmp_path)[0]
    assert event["dry_run"] is False
    assert event["executed"] is True
