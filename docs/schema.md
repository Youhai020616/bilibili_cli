# JSON Schema

`bili` commands return a stable envelope when `--json` is used.

## Success

```json
{
  "ok": true,
  "schema_version": "1",
  "command": "search",
  "strategy": "api",
  "fallback_used": false,
  "account": "default",
  "data": {}
}
```

Required fields:

- `ok`: always `true`
- `schema_version`: current envelope version
- `data`: command payload

Optional metadata:

- `command`
- `strategy`
- `fallback_used`
- `account`

## Error

```json
{
  "ok": false,
  "schema_version": "1",
  "command": "status",
  "strategy": "api",
  "error": {
    "code": "LOGIN_REQUIRED",
    "message": "Login is required for this operation",
    "retryable": true,
    "next_action": "Run `bili login` and retry"
  }
}
```

Required error fields:

- `ok`: always `false`
- `schema_version`
- `error.code`
- `error.message`
- `error.retryable`

Optional error fields:

- `error.next_action`
- `command`
- `strategy`

## Common Payload Shapes

- Search results: `items[]` with `title`, `bvid`, `aid`, `author`, `play`, `duration`.
- Video detail: `bvid`, `aid`, `title`, `owner`, `stat`, `pages`, `url`.
- Comments: `comments[]` with `rpid`, `member`, `message`, `like`, `reply_count`.
- Live info: `room_id`, `title`, `status`, `anchor`, `stream`.
- Publish tasks: `task_id`, `status`, `plan`.

The contract is intentionally small so agent clients can rely on the envelope first and the payload second.
