# Troubleshooting

## `LOGIN_REQUIRED`

Run `bili login` and retry the command with the same account.

## `SESSION_EXPIRED`

Your saved cookies are stale. Run `bili login` again.

## `CAPTCHA_REQUIRED`

Open a browser-backed login session with `bili login --browser` or retry later.

## `RATE_LIMITED`

Slow down requests, reduce `--count`, or wait before retrying.

## `ffmpeg` Missing

Install `ffmpeg` before using download or live recording commands.

## Playwright Missing Browser

Run `playwright install chromium` after installing the package.

## Search Index Expired

Re-run the original `bili search` command. Short numeric indexes are only valid while the cache entry is present.

## Download Has No Playable Stream

The video may require login, special permission, or a different quality selection. Try `bili video info --json` first and confirm the available pages and rights.

## Command Returned Dry-Run Plan

Write commands are dry-run by default. Add `--yes` only when you intend to execute the action.
