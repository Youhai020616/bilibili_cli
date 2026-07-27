---
name: bilibili
description: |
  Bilibili CLI skill for agent workflows: search, video detail, comments, danmaku,
  trending, login/session checks, and future download/live/publish actions.
metadata:
  trigger: Bilibili operations, video search, comments, danmaku, downloads, live rooms
---

# Bilibili CLI Skill

Use `bili` commands for Bilibili tasks. Prefer JSON output when another agent needs to parse results.

## Read Commands

```bash
bili search "keyword" --limit 10 --json
bili video info <bvid_or_index> --json
bili comments <bvid_or_index> --count 20 --json
bili danmaku <bvid_or_index> --format json
bili trending --count 20 --json
```

## Session Commands

```bash
bili login
bili status --json
bili me --json
bili browser open
```

## Short Index

After `bili search`, numeric indexes can be reused:

```bash
bili read 1
bili comments 1 --json
```

## Safety

For write actions, use dry-run first and require explicit confirmation before execution.
