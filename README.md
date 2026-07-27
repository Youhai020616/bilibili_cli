# bili-cli

Agent-ready Bilibili CLI with API-first read commands and Playwright fallback for browser/session flows.

## Install

```bash
pip install -e .
playwright install chromium
```

## Quick Start

```bash
bili init
bili doctor
bili search "AI programming" --limit 10
bili read 1
bili video info BV1xx411c7mD --json
bili comments BV1xx411c7mD --count 5
bili danmaku BV1xx411c7mD --format json
bili ranking --rid 0
bili hot-search
bili download BV1xx411c7mD --quality 360p --links-only --json
bili user info 2 --json
bili profile 2 --videos --limit 5 --json
bili live list --count 5 --json
bili live info <room_id> --json
bili publish -t "Title" -c "Desc" -v video.mp4 --dry-run
bili publish status <task_id>
bili trending --count 10
```

## Docs

- [Command reference](docs/commands.md)
- [Agent usage](docs/agent_usage.md)
- [JSON schema](docs/schema.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Release checklist](RELEASE_CHECKLIST.md)

## Commands

```bash
bili login
bili login --browser --browser-name chrome
bili status
bili me
bili logout
bili browser open

bili search "keyword" --type video --limit 20 --json
bili read 1
bili detail BVxxxx
bili video info BVxxxx
bili comments BVxxxx --count 20
bili video comments BVxxxx --count 20 --replies <rpid>
bili danmaku BVxxxx --page 1 --format ass -o danmaku.ass
bili download BVxxxx --quality 360p --output ~/Desktop
bili user info <mid>
bili user videos <mid> --limit 20
bili user followers <mid> --limit 20
bili user following <mid> --limit 20
bili user favorites <mid> --limit 20
bili profile <mid> --videos --followers --limit 5
bili live list --count 10
bili live info <room_id> --json
bili live streams <room_id> --show-urls --json
bili live danmaku <room_id> --count 20
bili live danmaku-conf <room_id> --json
bili live record <room_id> --duration 60
bili publish -t "Title" -c "Desc" -v video.mp4 --tags AI --dry-run
bili publish status <task_id>
bili creator open --page upload
bili creator videos --limit 20
bili creator delete <aid> --dry-run
bili analytics --video BVxxxx --json
bili analytics --json
bili notifications --json
bili messages --limit 20
bili like BVxxxx
bili coin BVxxxx --count 1
bili favorite folders
bili favorite add BVxxxx --folder <folder_id>
bili watchlater add BVxxxx
bili follow <mid>
bili comment post BVxxxx "comment text"
bili ranking --rid 0
bili hot-search
bili trending --source popular --count 20

bili account list
bili account add work
bili account default work
bili config show
```

## Architecture

```text
CLI commands
  -> services/API client/browser client
  -> session/account manager
  -> structured output and audit-ready errors
```

Read-heavy commands use Bilibili web APIs first. Login and browser-only flows use Playwright. Write actions are planned behind dry-run and confirmation gates.

Some space list endpoints may require a valid logged-in session or manual risk verification. Profile summary data uses public API surfaces where available and returns structured section errors when optional profile sections are blocked.

`ranking` uses the public ranking API first and falls back to a headless Playwright browser fetch when Bilibili returns a risk response.

Write commands are dry-run by default and write an audit event under `~/.bili/audit/`. Add `--yes` only when you intentionally want to execute the action with a valid logged-in Bilibili session.

Live stream URLs and danmaku connection tokens are treated as expiring private data. Stream URLs are hidden unless `--show-urls` or `--show-url` is provided; danmaku config reports only whether a token is present.

## Local State

```text
~/.bili/
  config.json
  accounts.json
  cookies/
  storage_state/
  cache/
  downloads/
  logs/
  audit/
```

Sensitive cookie values are never printed in normal output.
