"""Initialization and doctor commands."""

from __future__ import annotations

import importlib.util
import platform

import click

from bili_cli import __version__
from bili_cli.config import APP_DIR, CONFIG_PATH, init_config
from bili_cli.output import console, print_json, status, success, warning
from bili_cli.session import default_account, has_session
from bili_cli.utils.ffmpeg import ffmpeg_path


@click.command("init", help="Initialize local bili-cli config directories")
@click.option("--force", is_flag=True, help="Overwrite existing default config files")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def init(force: bool, as_json: bool) -> None:
    init_config(force=force)
    data = {"app_dir": str(APP_DIR), "config": str(CONFIG_PATH), "force": force}
    if as_json:
        print_json(data, command="init", strategy="local")
        return
    success(f"Initialized config at {APP_DIR}")


@click.command("doctor", help="Check local runtime prerequisites")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def doctor(as_json: bool) -> None:
    checks = [
        {"name": "python", "ok": True, "detail": platform.python_version()},
        {"name": "click", "ok": _has_module("click"), "detail": ""},
        {"name": "rich", "ok": _has_module("rich"), "detail": ""},
        {"name": "httpx", "ok": _has_module("httpx"), "detail": ""},
        {"name": "yaml", "ok": _has_module("yaml"), "detail": ""},
        {"name": "playwright", "ok": _has_module("playwright"), "detail": ""},
        {"name": "browser_cookie3", "ok": _has_module("browser_cookie3"), "detail": ""},
        {"name": "ffmpeg", "ok": bool(ffmpeg_path()), "detail": ffmpeg_path() or "not found"},
        {"name": "default_account", "ok": True, "detail": default_account()},
        {"name": "session", "ok": has_session(default_account()), "detail": "saved" if has_session(default_account()) else "missing"},
    ]
    data = {"version": __version__, "app_dir": str(APP_DIR), "checks": checks}
    if as_json:
        print_json(data, command="doctor", strategy="local")
        return
    console.rule("bili doctor")
    for item in checks:
        label = "OK" if item["ok"] else "MISS"
        style = "green" if item["ok"] else "yellow"
        status(item["name"], f"{label} {item['detail']}", style)
    if not bool(ffmpeg_path()):
        warning("ffmpeg is required for merged video/audio downloads")


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
