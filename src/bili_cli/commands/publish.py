"""Publish and creator-center commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from bili_cli import constants
from bili_cli.api.client import BiliAPIClient
from bili_cli.audit import write_audit_event
from bili_cli.browser.publisher import open_creator_page
from bili_cli.commands._common import fail, wants_json
from bili_cli.errors import APIError, BiliError, LoginRequiredError
from bili_cli.output import fmt_count, print_json, print_search_results, print_table, status, success
from bili_cli.publish_tasks import create_publish_task, list_publish_tasks, load_publish_task, update_publish_task


@click.group("publish", invoke_without_command=True, help="Create or inspect publish tasks")
@click.option("-t", "--title", default=None, help="Video title")
@click.option("-c", "--description", default="", help="Video description")
@click.option("-v", "--video", default=None, help="Video file path")
@click.option("--cover", default=None, help="Cover image path")
@click.option("--tags", multiple=True, help="Tag, repeat or comma-separate")
@click.option("--tid", type=int, default=None, help="Bilibili category/tid")
@click.option("--copyright", type=click.Choice(["original", "reprint"]), default="original", help="Copyright type")
@click.option("--source", default="", help="Source URL/description for reprint")
@click.option("--schedule", default=None, help="Scheduled publish time")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Open browser handoff for publishing")
@click.option("--headless", is_flag=True, help="Run browser handoff headless")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.pass_context
def publish_group(
    ctx: click.Context,
    title: str | None,
    description: str,
    video: str | None,
    cover: str | None,
    tags: tuple[str, ...],
    tid: int | None,
    copyright: str,
    source: str,
    schedule: str | None,
    dry_run: bool,
    yes: bool,
    headless: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    json_mode = wants_json(as_json, json_output)
    if not title or not video:
        raise click.UsageError("publish requires --title and --video when no subcommand is used")
    _run_publish(
        title=title,
        description=description,
        video=video,
        cover=cover,
        tags=tags,
        tid=tid,
        copyright=copyright,
        source=source,
        schedule=schedule,
        dry_run=dry_run,
        yes=yes,
        headless=headless,
        account=account,
        as_json=json_mode,
    )


@publish_group.command("status", help="Show a publish task")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def publish_status(task_id: str, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    try:
        task = load_publish_task(task_id)
    except BiliError as exc:
        fail(exc, as_json=json_mode, command="publish.status", strategy="local")
    if json_mode:
        print_json(task, command="publish.status", strategy="local")
    else:
        _print_publish_task(task)


@publish_group.command("tasks", help="List recent publish tasks")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def publish_tasks(limit: int, as_json: bool, json_output: bool) -> None:
    result = {"items": list_publish_tasks(limit=limit)}
    if wants_json(as_json, json_output):
        print_json(result, command="publish.tasks", strategy="local")
    else:
        rows = [[item.get("task_id"), item.get("status"), (item.get("plan") or {}).get("title")] for item in result["items"]]
        print_table("Publish tasks", ["Task", "Status", "Title"], rows)


@click.group("creator", help="Creator-center helpers")
def creator_group() -> None:
    pass


@creator_group.command("open", help="Open Bilibili creator center")
@click.option("--page", type=click.Choice(["home", "upload", "manager"]), default="home", help="Creator page")
@click.option("--headless", is_flag=True, help="Run browser headless")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def creator_open(page: str, headless: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    url = {
        "home": constants.CREATOR_HOME_URL,
        "upload": constants.CREATOR_UPLOAD_URL,
        "manager": constants.CREATOR_VIDEO_MANAGER_URL,
    }[page]
    _open_creator(url, account=account, headless=headless, as_json=wants_json(as_json, json_output), command="creator.open")


@creator_group.command("videos", help="List current account videos")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def creator_videos(limit: int, page: int, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    client = BiliAPIClient.from_config(account)
    try:
        auth = client.status()
        if not auth.get("is_login") or not auth.get("mid"):
            raise LoginRequiredError("Login is required to list creator videos")
        result = client.user_videos(auth["mid"], limit=limit, page=page)
    except BiliError as exc:
        fail(exc, as_json=json_mode, command="creator.videos", strategy="api")
    finally:
        client.close()
    if json_mode:
        print_json(result, command="creator.videos", strategy="api", account=account)
    else:
        print_search_results(result.get("items") or [], "creator videos")


@creator_group.command("delete", help="Prepare a creator-center delete handoff")
@click.argument("aid")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Open creator manager handoff")
@click.option("--headless", is_flag=True, help="Run browser handoff headless")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def creator_delete(aid: str, dry_run: bool, yes: bool, headless: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    dry = dry_run or not yes
    target = {"aid": aid, "manager_url": constants.CREATOR_VIDEO_MANAGER_URL}
    if dry:
        result = {"action": "creator.delete", "target": target, "dry_run": True, "executed": False, "next_action": "Re-run with --yes to open creator manager"}
        audit_path = write_audit_event(command="creator.delete", action="creator.delete", target=target, account=account, dry_run=True, strategy="browser", ok=True, result={"executed": False})
        result["audit_log"] = str(audit_path)
        _print_creator_result(result, as_json=json_mode, command="creator.delete", account=account)
        return
    try:
        handoff = open_creator_page(constants.CREATOR_VIDEO_MANAGER_URL, account=account, headless=headless)
    except BiliError as exc:
        write_audit_event(command="creator.delete", action="creator.delete", target=target, account=account, dry_run=False, strategy="browser", ok=False, error={"code": exc.code, "message": exc.message})
        fail(exc, as_json=json_mode, command="creator.delete", strategy="browser")
    result = {"action": "creator.delete", "target": target, "dry_run": False, "executed": True, "browser": handoff}
    audit_path = write_audit_event(command="creator.delete", action="creator.delete", target=target, account=account, dry_run=False, strategy="browser", ok=True, result={"manual_required": True})
    result["audit_log"] = str(audit_path)
    _print_creator_result(result, as_json=json_mode, command="creator.delete", account=account)


def _run_publish(
    *,
    title: str,
    description: str,
    video: str,
    cover: str | None,
    tags: tuple[str, ...],
    tid: int | None,
    copyright: str,
    source: str,
    schedule: str | None,
    dry_run: bool,
    yes: bool,
    headless: bool,
    account: str | None,
    as_json: bool,
) -> None:
    try:
        plan = build_publish_plan(
            title=title,
            description=description,
            video=video,
            cover=cover,
            tags=tags,
            tid=tid,
            copyright=copyright,
            source=source,
            schedule=schedule,
        )
    except BiliError as exc:
        fail(exc, as_json=as_json, command="publish", strategy="local")
    dry = dry_run or not yes
    task = create_publish_task(plan, status="planned" if dry else "browser_handoff")
    target = {"task_id": task["task_id"], "title": plan["title"], "video": plan["video"]["path"]}
    if dry:
        audit_path = write_audit_event(command="publish", action="publish.plan", target=target, account=account, dry_run=True, strategy="browser", ok=True, result={"executed": False})
        result = {"task": task, "dry_run": True, "executed": False, "audit_log": str(audit_path), "next_action": "Re-run with --yes to open creator upload page"}
        _print_publish_result(result, as_json=as_json, account=account)
        return
    try:
        handoff = open_creator_page(constants.CREATOR_UPLOAD_URL, account=account, headless=headless, upload_file=plan["video"]["path"])
    except BiliError as exc:
        write_audit_event(command="publish", action="publish.handoff", target=target, account=account, dry_run=False, strategy="browser", ok=False, error={"code": exc.code, "message": exc.message})
        fail(exc, as_json=as_json, command="publish", strategy="browser")
    task = update_publish_task(task["task_id"], status="browser_handoff", result=handoff)
    audit_path = write_audit_event(command="publish", action="publish.handoff", target=target, account=account, dry_run=False, strategy="browser", ok=True, result={"manual_required": True})
    result = {"task": task, "browser": handoff, "dry_run": False, "executed": True, "audit_log": str(audit_path)}
    _print_publish_result(result, as_json=as_json, account=account)


def build_publish_plan(
    *,
    title: str,
    description: str,
    video: str,
    cover: str | None,
    tags: tuple[str, ...],
    tid: int | None,
    copyright: str,
    source: str,
    schedule: str | None,
) -> dict[str, Any]:
    video_path = Path(video).expanduser()
    if not video_path.exists() or not video_path.is_file():
        raise APIError(f"Video file not found: {video}", "UNSUPPORTED_INPUT")
    cover_data = None
    if cover:
        cover_path = Path(cover).expanduser()
        if not cover_path.exists() or not cover_path.is_file():
            raise APIError(f"Cover file not found: {cover}", "UNSUPPORTED_INPUT")
        cover_data = {"path": str(cover_path), "size": cover_path.stat().st_size}
    return {
        "title": title,
        "description": description,
        "video": {"path": str(video_path), "size": video_path.stat().st_size, "suffix": video_path.suffix.lower()},
        "cover": cover_data,
        "tags": _split_tags(tags),
        "tid": tid,
        "copyright": copyright,
        "source": source,
        "schedule": schedule,
        "manual_required": True,
    }


def _split_tags(tags: tuple[str, ...]) -> list[str]:
    result: list[str] = []
    for entry in tags:
        result.extend([item.strip() for item in entry.split(",") if item.strip()])
    return list(dict.fromkeys(result))


def _open_creator(url: str, *, account: str | None, headless: bool, as_json: bool, command: str) -> None:
    try:
        result = open_creator_page(url, account=account, headless=headless)
    except BiliError as exc:
        fail(exc, as_json=as_json, command=command, strategy="browser")
    if as_json:
        print_json(result, command=command, strategy="browser", account=account)
    else:
        success("Creator browser handoff finished")
        status("URL", result.get("url"))


def _print_publish_result(result: dict[str, Any], *, as_json: bool, account: str | None) -> None:
    if as_json:
        print_json(result, command="publish", strategy="browser", account=account)
        return
    success("Publish dry run prepared" if result.get("dry_run") else "Creator browser handoff finished")
    _print_publish_task(result["task"])
    status("Audit", result.get("audit_log"))
    if result.get("next_action"):
        status("Next", result.get("next_action"))


def _print_publish_task(task: dict[str, Any]) -> None:
    plan = task.get("plan") or {}
    video = plan.get("video") or {}
    status("Task", task.get("task_id"))
    status("Status", task.get("status"))
    status("Title", plan.get("title"))
    status("Video", f"{video.get('path')} ({fmt_count(video.get('size'))} bytes)")


def _print_creator_result(result: dict[str, Any], *, as_json: bool, command: str, account: str | None) -> None:
    if as_json:
        print_json(result, command=command, strategy="browser", account=account)
        return
    success("Creator dry run prepared" if result.get("dry_run") else "Creator browser handoff finished")
    status("Action", result.get("action"))
    status("Audit", result.get("audit_log"))
    if result.get("next_action"):
        status("Next", result.get("next_action"))
