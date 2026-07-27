"""Command shared helpers."""

from __future__ import annotations

from bili_cli.errors import BiliError
from bili_cli.output import error, print_error_json, status


def fail(exc: BiliError, *, as_json: bool = False, command: str | None = None, strategy: str | None = None) -> None:
    if as_json:
        print_error_json(exc, command=command, strategy=strategy)
    else:
        error(f"{exc.code}: {exc.message}")
        if exc.next_action:
            status("Next", exc.next_action)
    raise SystemExit(1)


def wants_json(as_json: bool, json_output: bool) -> bool:
    return bool(as_json or json_output)
