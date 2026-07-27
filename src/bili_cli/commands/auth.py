"""Authentication and browser session commands."""

from __future__ import annotations

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.browser.login import login_with_browser, open_browser_session
from bili_cli.commands._common import fail
from bili_cli.errors import BiliError
from bili_cli.output import info, print_json, status as print_status, success, warning
from bili_cli.session import account_name, clear_session, cookie_path, has_session, storage_state_path


@click.command("login", help="Open a headed browser and save Bilibili login session")
@click.option("--account", default=None, help="Account profile name")
@click.option("--timeout", type=int, default=None, help="Seconds to wait for login")
@click.option("--headless", is_flag=True, help="Run browser headless")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def login(account: str | None, timeout: int | None, headless: bool, as_json: bool) -> None:
    name = account_name(account)
    if not as_json:
        info("Opening browser. Log in to Bilibili manually if required.")
    try:
        result = login_with_browser(account=name, timeout=timeout, headless=headless)
    except BiliError as exc:
        fail(exc, as_json=as_json, command="login", strategy="browser")
    if as_json:
        print_json(result, command="login", strategy="browser", account=name)
        return
    if result.get("logged_in"):
        success(f"Login session saved for {name}")
    else:
        warning(f"Login not detected before timeout, but browser state was saved for {name}")
    print_status("Cookies", result.get("cookies", 0))
    print_status("Cookie file", cookie_path(name))
    print_status("Storage state", storage_state_path(name))


@click.command("status", help="Check login status")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def auth_status(account: str | None, as_json: bool) -> None:
    name = account_name(account)
    client = BiliAPIClient.from_config(name)
    try:
        result = client.status()
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command="status", strategy="api")
    finally:
        client.close()
    result["has_local_session"] = has_session(name)
    if as_json:
        print_json(result, command="status", strategy="api", account=name)
        return
    print_status("Account", name)
    print_status("Local session", "yes" if result["has_local_session"] else "no", "green" if result["has_local_session"] else "yellow")
    print_status("Login status", "logged in" if result.get("is_login") else "not logged in", "green" if result.get("is_login") else "yellow")
    if result.get("is_login"):
        print_status("User", f"{result.get('uname')} ({result.get('mid')})")


@click.command("me", help="Show current logged-in user")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def me(account: str | None, as_json: bool) -> None:
    auth_status.callback(account=account, as_json=as_json)


@click.command("logout", help="Remove saved local session")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def logout(account: str | None, as_json: bool) -> None:
    name = account_name(account)
    clear_session(name)
    if as_json:
        print_json({"account": name, "logged_out": True}, command="logout", strategy="local", account=name)
    else:
        success(f"Removed local session for {name}")


@click.group("browser", help="Browser session helpers")
def browser_group() -> None:
    pass


@browser_group.command("open", help="Open Bilibili with saved browser session")
@click.option("--account", default=None, help="Account profile name")
@click.option("--headless", is_flag=True, help="Open browser headless")
def browser_open(account: str | None, headless: bool) -> None:
    name = account_name(account)
    try:
        open_browser_session(account=name, headless=headless)
    except BiliError as exc:
        fail(exc, command="browser.open", strategy="browser")
