---
name: bilibili
description: |
  Bilibili CLI skill for agent workflows: search, video detail, comments, danmaku,
  download, live, publish, interactions, analytics, and session checks.
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
bili user info <mid> --json
bili live info <room_id> --json
bili analytics --video BVxxxx --json
```

## Session Commands

```bash
bili login
bili login --browser
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

## Write Commands

Use dry-run first, then add `--yes` only after confirming the target.

```bash
bili like BVxxxx --dry-run
bili coin BVxxxx --count 1 --dry-run
bili favorite add BVxxxx --folder <folder_id> --dry-run
bili watchlater add BVxxxx --dry-run
bili follow <mid> --dry-run
bili comment post BVxxxx "content" --dry-run
bili publish -t "Title" -c "Desc" -v video.mp4 --dry-run
```

## Browser Flows

Use Playwright-backed commands when the API is blocked or a human review step is needed:

```bash
bili download BVxxxx --quality 1080p
bili live record <room_id> --duration 60
bili publish status <task_id>
bili creator open --page upload
```

## Safety

For write actions, use dry-run first and require explicit confirmation before execution.
