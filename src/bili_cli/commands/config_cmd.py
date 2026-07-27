"""Config commands."""

from __future__ import annotations

import json

import click

from bili_cli.config import get_value, load_config, reset_config, set_value
from bili_cli.output import console, print_json, success


@click.group("config", help="Manage local config")
def config_group() -> None:
    pass


@config_group.command("show", help="Show config")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def show(as_json: bool) -> None:
    data = load_config()
    if as_json:
        print_json(data, command="config.show", strategy="local")
    else:
        console.print_json(json.dumps(data, ensure_ascii=False, indent=2))


@config_group.command("get", help="Get config value")
@click.argument("key")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def get(key: str, as_json: bool) -> None:
    value = get_value(key)
    data = {"key": key, "value": value}
    if as_json:
        print_json(data, command="config.get", strategy="local")
    else:
        console.print(value)


@config_group.command("set", help="Set config value")
@click.argument("key")
@click.argument("value")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def set_cmd(key: str, value: str, as_json: bool) -> None:
    set_value(key, value)
    data = {"key": key, "value": get_value(key)}
    if as_json:
        print_json(data, command="config.set", strategy="local")
    else:
        success(f"Set {key}")


@config_group.command("reset", help="Reset config")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def reset(as_json: bool) -> None:
    reset_config()
    if as_json:
        print_json({"reset": True}, command="config.reset", strategy="local")
    else:
        success("Config reset")
