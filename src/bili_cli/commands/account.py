"""Account management commands."""

from __future__ import annotations

import click

from bili_cli.output import print_json, print_table, status, success
from bili_cli.session import add_account, default_account, has_session, list_accounts, remove_account, set_default_account


@click.group("account", help="Manage local account profiles")
def account_group() -> None:
    pass


@account_group.command("list", help="List accounts")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def list_cmd(as_json: bool) -> None:
    default = default_account()
    accounts = [{"name": name, "default": name == default, "has_session": has_session(name)} for name in list_accounts()]
    if as_json:
        print_json({"accounts": accounts}, command="account.list", strategy="local")
        return
    rows = [[item["name"], "yes" if item["default"] else "", "yes" if item["has_session"] else ""] for item in accounts]
    print_table("Accounts", ["Name", "Default", "Session"], rows)


@account_group.command("add", help="Add an account profile")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def add(name: str, as_json: bool) -> None:
    add_account(name)
    if as_json:
        print_json({"name": name}, command="account.add", strategy="local")
    else:
        success(f"Added account {name}")


@account_group.command("remove", help="Remove an account profile and its saved session")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def remove(name: str, as_json: bool) -> None:
    remove_account(name)
    if as_json:
        print_json({"name": name}, command="account.remove", strategy="local")
    else:
        success(f"Removed account {name}")


@account_group.command("default", help="Set default account")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def default(name: str, as_json: bool) -> None:
    set_default_account(name)
    if as_json:
        print_json({"default": name}, command="account.default", strategy="local")
    else:
        success(f"Default account: {name}")


@account_group.command("current", help="Show current default account")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def current(as_json: bool) -> None:
    account = default_account()
    if as_json:
        print_json({"default": account, "has_session": has_session(account)}, command="account.current", strategy="local")
    else:
        status("Default account", account)
