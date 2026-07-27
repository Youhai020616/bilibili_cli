"""bili command entrypoint."""

from __future__ import annotations

import click

from bili_cli import __version__

BANNER = rf"""
  +-------------------------------+
  |   bili-cli v{__version__:<18} |
  |   Bilibili command line tool  |
  +-------------------------------+
"""


class AliasGroup(click.Group):
    """Click group with short aliases."""

    ALIASES = {
        "s": "search",
        "dl": "download",
        "r": "read",
        "t": "trending",
        "acc": "account",
        "cfg": "config",
        "dm": "danmaku",
        "stat": "status",
        "u": "user",
        "p": "profile",
        "fav": "favorite",
        "wl": "watchlater",
        "lv": "live",
        "pub": "publish",
        "cr": "creator",
        "ana": "analytics",
        "msg": "messages",
        "rank": "ranking",
        "hs": "hot-search",
    }

    def get_command(self, ctx: click.Context, cmd_name: str):
        resolved = self.ALIASES.get(cmd_name, cmd_name)
        return super().get_command(ctx, resolved)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        formatter.write(BANNER)
        super().format_help(ctx, formatter)


@click.group(cls=AliasGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="bili-cli")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Agent-ready Bilibili CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


from bili_cli.commands.account import account_group
from bili_cli.commands.auth import auth_status, browser_group, login, logout, me
from bili_cli.commands.config_cmd import config_group
from bili_cli.commands.danmaku import danmaku
from bili_cli.commands.download import download
from bili_cli.commands.init import doctor, init
from bili_cli.commands.interact import coin, comment_group, favorite_group, follow, like, watchlater_group
from bili_cli.commands.live import live_group
from bili_cli.commands.analytics import analytics, messages, notifications
from bili_cli.commands.publish import creator_group, publish_group
from bili_cli.commands.search import search
from bili_cli.commands.trending import hot_search, ranking, trending
from bili_cli.commands.user import profile, user_group
from bili_cli.commands.video import comments, detail, read, video_group

cli.add_command(init)
cli.add_command(doctor)
cli.add_command(login)
cli.add_command(auth_status, "status")
cli.add_command(me)
cli.add_command(logout)
cli.add_command(browser_group, "browser")
cli.add_command(account_group, "account")
cli.add_command(config_group, "config")
cli.add_command(search)
cli.add_command(video_group, "video")
cli.add_command(detail)
cli.add_command(read)
cli.add_command(comments)
cli.add_command(danmaku)
cli.add_command(download)
cli.add_command(trending)
cli.add_command(ranking)
cli.add_command(hot_search)
cli.add_command(user_group, "user")
cli.add_command(profile)
cli.add_command(like)
cli.add_command(coin)
cli.add_command(follow)
cli.add_command(favorite_group, "favorite")
cli.add_command(watchlater_group, "watchlater")
cli.add_command(comment_group, "comment")
cli.add_command(live_group, "live")
cli.add_command(publish_group, "publish")
cli.add_command(creator_group, "creator")
cli.add_command(analytics)
cli.add_command(notifications)
cli.add_command(messages)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
