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
bili trending --count 10
```

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
