# bilibili_cli Development Plan

目标：把 Bilibili 做成一个对 agent 友好的成熟 CLI 项目，能力完整度对标现有 `dy-cli`，而不是只完成搜索/详情/评论的 MVP。

核心原则：

- 业务命令优先，不暴露页面选择器、接口签名、Cookie 细节。
- 读操作 API 优先，必要时 Playwright 兜底。
- 登录、投稿、评论发布、点赞、投币、收藏、关注等账号写操作默认走有头浏览器或经过验证的安全 API 路径。
- 所有命令都支持人类可读输出和 `--json` 机器可读输出。
- 高风险写操作必须支持 `--dry-run`、`--yes`、审计日志和限速。
- 不绕过验证码、会员权限、付费墙或访问控制；遇到验证时转交用户手动完成。

## 1. Product Positioning

`bili` 不是通用浏览器点击器，而是 Bilibili 的业务 CLI：

```bash
bili search "AI 编程" --limit 10
bili video info BVxxxx --json
bili video comments BVxxxx --count 20 --json
bili danmaku BVxxxx --page 1 --format ass
bili download BVxxxx --quality 1080p --output ~/Desktop
bili live list --keyword "编程"
bili live info <room_id> --json
bili comment post BVxxxx "这个讲解很系统" --dry-run
```

Agent 使用方式：

```text
用户自然语言
  -> Claude / Codex
  -> bili CLI structured commands
  -> API client / Playwright client
  -> Bilibili
```

## 2. Scope Parity With dy-cli

现有 `dy-cli` 成熟能力包括：

- 搜索、短索引、详情、评论
- 下载、批量下载、导出
- 登录、状态、退出、多账号
- 点赞、收藏、评论、关注
- 热榜、直播列表、直播信息、直播录制
- 发布视频/图文
- 用户主页、我的信息
- 数据看板、通知
- 配置管理、结构化 JSON 输出、Skill 文档

`bili` 的 v1.0 应覆盖同等成熟度，但要体现 B 站平台特色：

- `BV/AV/AID/CID/EP/SS` 多 ID 体系
- 多 P 视频、合集、番剧/课程/OGV
- 弹幕 `danmaku`
- DASH 音视频分离下载和 `ffmpeg` 合并
- 评论楼中楼
- 投币、收藏夹、稍后再看
- 直播间弹幕、舰长/礼物/在线状态
- 创作中心投稿、稿件管理、数据看板

## 3. Platform Research Notes

### Official Surfaces

- Bilibili 开放平台提供 OAuth 2.0 接入能力，适合正式授权和基础开放信息接入。
- Bilibili 直播开放平台提供官方直播互动相关 API，并要求统一鉴权、签名和生命周期管理。
- 官方开放能力和网页内部接口不是一回事。开发时优先使用官方能力；没有官方能力时，才考虑网页接口或 Playwright。

### Observed Web/API Characteristics

需要在实现时持续验证：

- 视频详情接口可按 `bvid` 返回 `aid`、`cid`、标题、作者、统计、分 P 信息等结构化数据。
- 评论接口通常以 `type=1`、`oid=aid` 获取视频评论，并支持分页和楼中楼。
- 热门/排行榜接口可作为 `trending` 的候选来源。
- 搜索、空间投稿、部分排行榜、下载高画质等路径可能受 UA、Cookie、WBI 签名、referer、频控和登录态影响。
- 下载地址有时效性；高画质、会员视频、课程、番剧可能需要登录或权限。
- 写操作通常涉及 `csrf`、Cookie、风险校验和频控，不能默认批量执行。

### Existing Ecosystem To Learn From

- `yt-dlp`: Bilibili 下载、字幕、弹幕、番剧提取经验丰富，可作为下载器设计参考。
- `biliup-rs` / `biliup`: Bilibili 投稿、下载、登录信息维护、上传流程可以作为投稿模块参考。
- Bilibili 直播开放平台文档：直播互动、长连接、签名、事件协议参考。

## 4. Architecture

```text
CLI commands
  -> command handlers
  -> service layer
  -> platform adapter
      -> api client
      -> browser client
      -> downloader
      -> uploader
      -> live client
  -> session/account manager
  -> output/error envelope
  -> audit/log/fixtures
```

Recommended package structure:

```text
bilibili_cli/
  pyproject.toml
  README.md
  DEVELOPMENT_PLAN.md
  SKILL.md
  src/
    bili_cli/
      __init__.py
      main.py
      constants.py
      errors.py
      models.py
      output.py
      config.py
      session.py
      index_cache.py
      audit.py
      rate_limit.py
      utils/
        ids.py
        time.py
        sanitize.py
        export.py
        ffmpeg.py
        http.py
        wbi.py
      api/
        client.py
        auth.py
        search.py
        video.py
        comments.py
        danmaku.py
        user.py
        ranking.py
        live.py
        favorite.py
        interact.py
        creator.py
      browser/
        client.py
        login.py
        actions.py
        publisher.py
        creator_center.py
        capture.py
      downloader/
        streams.py
        download.py
        merge.py
        subtitles.py
        danmaku.py
      uploader/
        video.py
        cover.py
        metadata.py
      commands/
        init.py
        auth.py
        account.py
        config_cmd.py
        search.py
        video.py
        comments.py
        danmaku.py
        download.py
        trending.py
        live.py
        user.py
        interact.py
        publish.py
        analytics.py
        notifications.py
        doctor.py
  tests/
    unit/
    integration/
    contract/
    fixtures/
  docs/
    commands.md
    agent_usage.md
    platform_notes.md
    troubleshooting.md
```

## 5. Command Map

### 5.1 Init / Help

```bash
bili init
bili --help
bili doctor
```

Requirements:

- `init` creates config dirs and default config.
- `doctor` checks Python version, Playwright install, browser availability, `ffmpeg`, network access, saved accounts, and session freshness.

### 5.2 Auth / Session

```bash
bili login
bili login --account work
bili login --browser
bili status
bili me
bili logout
bili browser open
bili browser open --account work
```

Implementation:

- `login`: Playwright headed login, save cookies and storage state.
- `status`: call account/nav/status endpoint with saved session.
- `me`: normalized current user info.
- `browser open`: open current saved session for manual validation.
- Never print cookies, CSRF tokens, or signed URLs in normal output.

### 5.3 Multi-Account

```bash
bili account list
bili account add work
bili account remove work
bili account default work
bili account current
```

Requirements:

- Isolated cookie and storage state per account.
- Every command supports `--account`.
- JSON output includes `account` and `login_required` when relevant.

### 5.4 Config

```bash
bili config show
bili config get api.timeout
bili config set api.proxy http://127.0.0.1:7897
bili config reset
```

Config areas:

- API timeout, retries, proxy
- browser headless/headed default
- download dir
- export dir
- rate limits
- default account
- JSON output defaults

### 5.5 Search

```bash
bili search "Claude Code"
bili search "AI 编程" --type video --limit 20
bili search "AI 编程" --type user
bili search "AI 编程" --type live
bili search "AI 编程" --sort views --time week --json
bili search "AI 编程" -o results.csv
```

Types:

- `video`
- `user`
- `live`
- `article`
- `bangumi`

Requirements:

- API first.
- Browser fallback when API returns captcha/risk/HTML instead of JSON.
- Cache results for short-index commands.
- Normalize search output fields.
- Support `json`, `csv`, `yaml`.

### 5.6 Short Index / Read

```bash
bili read 1
bili r 1
bili video info 1
bili download 1
bili comments 1
```

Requirements:

- After `bili search`, numeric indexes map to cached result IDs.
- Cache must record query, timestamp, item type, canonical URL, `bvid`, `aid`, `cid`, `mid`.
- Expired cache should fail clearly.

### 5.7 Video Detail

```bash
bili video info BVxxxx
bili video info av123456
bili video pages BVxxxx
bili video tags BVxxxx
bili video related BVxxxx --limit 10
bili detail BVxxxx
```

Requirements:

- Normalize `BV`, `av/aid`, short links, full URLs.
- Return `bvid`, `aid`, title, description, owner, stats, duration, pubdate, pages, `cid`, tags, rights, cover, canonical URL.
- Support multi-P pages.
- Distinguish UGC video, OGV/bangumi, course, paid/permission-limited content.

### 5.8 Comments

```bash
bili comments BVxxxx --count 20
bili video comments BVxxxx --count 20 --sort hot
bili video comments BVxxxx --replies <rpid> --count 20
bili video comments BVxxxx --json
bili video comments BVxxxx -o comments.csv
```

Requirements:

- API first using video `aid` as comment `oid`.
- Support newest/hot sort when available.
- Support pagination and reply threads.
- Normalize `rpid`, user, `mid`, content, likes, reply count, created time, location/IP label if present.
- Browser fallback only when API is blocked or needs page context.

### 5.9 Danmaku

Bilibili-specific feature; this should be first-class, not an afterthought.

```bash
bili danmaku BVxxxx
bili danmaku BVxxxx --page 2
bili danmaku BVxxxx --format json
bili danmaku BVxxxx --format xml -o danmaku.xml
bili danmaku BVxxxx --format ass -o danmaku.ass
bili danmaku send BVxxxx "前方高能" --time 35.2 --dry-run
```

Requirements:

- Fetch danmaku by `cid`.
- Export `json`, `xml`, `ass`.
- Optional conversion to `.ass` for video embedding.
- Send danmaku is a write action: dry-run by default, account required, audit required.

### 5.10 Download

```bash
bili download BVxxxx --output ~/Desktop
bili download BVxxxx --page all --quality 1080p
bili download BVxxxx --audio-only
bili download BVxxxx --cover
bili download BVxxxx --subtitle
bili download BVxxxx --danmaku ass
bili download BVxxxx --with-metadata
bili download BVxxxx --json
```

Requirements:

- API playurl first.
- Support DASH video/audio streams.
- Select quality by user preference and available permissions.
- Merge video/audio with `ffmpeg`.
- Support multi-P videos.
- Support subtitles and danmaku sidecar files.
- Support resume/retry.
- Clear error when `ffmpeg` is missing.
- Never claim premium/high-quality download if account lacks permission.

Optional fallback:

- Integrate or shell out to `yt-dlp` behind a feature flag for difficult downloads.
- Keep native downloader as the default path for agent-friendly structured output.

### 5.11 Trending / Ranking

```bash
bili trending
bili trending --count 50
bili trending --category tech
bili ranking --rid 0
bili ranking --rid 36 --json
bili popular --count 20
bili hot-search
```

Requirements:

- API first.
- Support popular list, ranking list, categories, hot search words.
- Export support.
- Watch mode optional:

```bash
bili trending --watch --interval 300
```

### 5.12 User / Profile

```bash
bili user info <mid>
bili user videos <mid> --limit 30
bili user favorites <mid> --limit 20
bili user following <mid> --limit 20
bili user followers <mid> --limit 20
bili profile <mid> --videos
```

Requirements:

- API first.
- WBI/signature support may be required for space endpoints.
- Browser fallback for endpoints that consistently fail without page context.
- Normalize profile stats, official verification, level, avatar, sign, videos.

### 5.13 Interactions

```bash
bili like BVxxxx --dry-run
bili like BVxxxx --unlike --dry-run
bili coin BVxxxx --count 1 --dry-run
bili favorite folders
bili favorite add BVxxxx --folder <folder_id> --dry-run
bili favorite remove BVxxxx --folder <folder_id> --dry-run
bili watchlater add BVxxxx --dry-run
bili follow <mid> --dry-run
bili comment post BVxxxx "内容" --dry-run
bili comment delete <rpid> --dry-run
```

Rules:

- Default `--dry-run` for all account write operations.
- Require `--yes` to execute.
- Prefer Playwright path at first for behavior that is sensitive to risk checks.
- API path can be enabled only after verified tests and clear rollback/error handling.
- Every write records an audit event with command, target, account, dry-run/executed, timestamp, strategy, result.
- Do not support mass-like/mass-follow by default.

### 5.14 Live

```bash
bili live list
bili live list --keyword "编程" --count 20
bili live info <room_id>
bili live streams <room_id> --json
bili live record <room_id> --output ~/Desktop
bili live danmaku <room_id> --duration 60
```

Requirements:

- Support room listing/search when stable.
- `info` returns anchor, title, status, online count, cover, room id, uid, stream URLs if available.
- `record` uses stream URL + `ffmpeg`.
- Live danmaku listener can use official live open platform when the user configures official credentials; otherwise mark as experimental/browser-derived.
- Do not expose full expiring stream URLs by default unless `--json` or `--show-url` is requested.

### 5.15 Publish / Creator Center

```bash
bili publish -t "标题" -c "简介" -v video.mp4 --dry-run
bili publish -t "标题" -c "简介" -v video.mp4 --tags AI --tid 36
bili publish -t "标题" -c "简介" -v video.mp4 --cover cover.jpg
bili publish --schedule "2026-08-01T10:00:00+08:00" ...
bili publish status <task_id>
bili creator videos --limit 20
bili creator delete <aid> --dry-run
```

Implementation:

- Phase 1: Playwright creator-center upload path.
- Phase 2: evaluate `biliup` / uploader protocol compatibility.
- Support cover, tags, category/tid, source, copyright/no-reprint, dynamic text, visibility, schedule where Bilibili supports it.
- Upload must have resumable logs and a final confirmation screen.

### 5.16 Analytics / Notifications

```bash
bili analytics
bili analytics --video BVxxxx
bili analytics --csv data.csv
bili notifications
bili messages
```

Implementation:

- Playwright + XHR interception first, because creator center APIs and message center may be account/UI-bound.
- Output only normalized summary unless `--json` is requested.
- Avoid storing private message content unless explicitly exported.

## 6. Output Contract

All commands should support:

```bash
--json
--debug
--timeout <seconds>
--account <name>
--output <path>
```

Success envelope:

```json
{
  "ok": true,
  "schema_version": "1",
  "command": "video.comments",
  "strategy": "api",
  "fallback_used": false,
  "account": "default",
  "data": {}
}
```

Error envelope:

```json
{
  "ok": false,
  "schema_version": "1",
  "command": "video.comments",
  "strategy": "api",
  "error": {
    "code": "LOGIN_REQUIRED",
    "message": "Login is required for this operation",
    "retryable": true,
    "next_action": "Run `bili login` and retry"
  }
}
```

Common error codes:

- `LOGIN_REQUIRED`
- `SESSION_EXPIRED`
- `CAPTCHA_REQUIRED`
- `RATE_LIMITED`
- `PERMISSION_DENIED`
- `VIDEO_NOT_FOUND`
- `COMMENT_NOT_FOUND`
- `UNSUPPORTED_CONTENT_TYPE`
- `FFMPEG_MISSING`
- `DOWNLOAD_URL_EXPIRED`
- `API_SCHEMA_CHANGED`
- `BROWSER_FALLBACK_FAILED`
- `WRITE_CONFIRMATION_REQUIRED`

## 7. Session Storage

Use local config:

```text
~/.bili/
  config.json
  accounts.json
  cookies/
    default.json
    work.json
  storage_state/
    default.json
    work.json
  cache/
    search_index.json
    endpoint_health.json
  downloads/
  logs/
  audit/
  fixtures/
```

Rules:

- Never commit local session files.
- Redact `SESSDATA`, `bili_jct`, `DedeUserID`, stream URLs, and signed URLs in logs.
- `--debug` may write redacted request metadata, not raw credential material.

## 8. API / Browser Strategy Matrix

| Feature | Primary | Fallback | Notes |
|---|---|---|---|
| login | Playwright | manual browser import | QR/password/phone verification should be user-driven |
| status/me | API | browser page check | read saved session |
| search | API | browser network/DOM | search may require browser context |
| video info | API | browser DOM/API capture | public read |
| comments | API | browser DOM/API capture | use `aid` as `oid` |
| danmaku read | API | none/browser | depends on `cid` |
| download | API | yt-dlp optional | DASH + ffmpeg |
| trending/ranking | API | browser capture | public lists |
| user profile/videos | API | browser capture | WBI may be required |
| live list/info | API | browser capture | stream URLs expire |
| live record | API + ffmpeg | browser captured URL | preserve user permissions |
| like/favorite/coin/follow | Playwright first | verified API later | write action gates |
| comment post/delete | Playwright first | verified API later | dry-run/audit |
| publish | Playwright first | uploader protocol later | creator center |
| analytics/messages | Playwright/XHR | API if verified | private account data |

## 9. Testing Strategy

### Unit Tests

- ID parser: BV, AV, AID, CID, EP, SS, URLs, short links.
- Output envelopes.
- Error mapping.
- Search result normalization.
- Video detail normalization.
- Comment and reply normalization.
- Danmaku parsing/export.
- Download stream selection.
- File naming and sanitization.
- Account/config storage.

### Contract Tests

- Golden response fixtures for each API adapter.
- Detect schema drift: missing required fields, renamed fields, changed pagination.
- Validate command JSON schema.

### Integration Tests

Use a small public fixture set:

```bash
bili status --json
bili search "AI" --limit 3 --json
bili video info <known_bvid> --json
bili video comments <known_bvid> --count 5 --json
bili danmaku <known_bvid> --page 1 --format json
bili trending --count 5 --json
```

### Manual Tests

- Login with headed browser.
- Open saved browser session.
- Download one short public video.
- Download one multi-P video.
- Export comments to CSV.
- Record a live room for 10 seconds.
- Dry-run all write actions.
- Execute one low-risk write action only with explicit user confirmation.

### CI

- Unit and contract tests run in CI.
- Live integration tests are opt-in because they depend on network, platform state, cookies, and rate limits.

## 10. Release Milestones

### Milestone 0: Scaffold

- Package skeleton.
- Click/Typer CLI.
- Config/session/output/error modules.
- `bili init`, `bili doctor`.
- README and install docs.

### Milestone 1: Read-Only Core

- `search`
- `read`
- `video info`
- `comments`
- `danmaku`
- `trending`
- JSON/CSV/YAML export.
- Unit and contract tests.

### Milestone 2: Auth And Accounts

- `login`
- `status`
- `me`
- `logout`
- `browser open`
- multi-account commands.
- API requests can reuse saved cookies.

### Milestone 3: Download

- Native playurl downloader.
- DASH stream selection.
- `ffmpeg` merge.
- subtitles, cover, danmaku sidecars.
- multi-P support.
- optional `yt-dlp` fallback flag.

### Milestone 4: User And Collections

- user info.
- user videos.
- favorite folders.
- watch later.
- collection/favorite read paths.

### Milestone 5: Interactions

- like/unlike.
- coin.
- favorite add/remove.
- follow/unfollow.
- comment post/delete.
- dry-run, confirmation, audit.

### Milestone 6: Live

- live list/search.
- room info.
- stream URL extraction.
- live recording.
- live danmaku listener.
- optional official live open platform credential support.

### Milestone 7: Publish

- creator-center upload through Playwright.
- cover/tags/category/desc/copyright.
- task logs and publish status.
- evaluate uploader protocol or `biliup` compatibility.

### Milestone 8: Analytics / Notifications

- creator dashboard summary.
- video analytics.
- notifications/messages summary.
- CSV/JSON export.

### Milestone 9: Agent Readiness And Release

- `SKILL.md`.
- command reference docs.
- troubleshooting docs.
- schema docs.
- CI.
- PyPI packaging.
- release checklist.

## 11. Mature v1.0 Definition Of Done

The project is v1.0-ready when:

- All core commands have human and JSON output.
- Search result short index works across detail/comments/download/like.
- Login and multi-account flows are reliable.
- API failures return structured errors and useful next actions.
- At least one browser fallback exists for search/comments/user profile.
- Downloads support public video, multi-P video, cover, subtitles/danmaku, and ffmpeg merge.
- Live info and short recording work.
- Write actions are protected by dry-run, confirmation, rate limits, and audit logs.
- README, `SKILL.md`, and command docs are complete.
- Unit tests and contract tests pass.
- Integration test checklist has been manually verified with a logged-in account.

## 12. Safety / Compliance Boundaries

- Do not bypass CAPTCHA or phone verification.
- Do not bypass paywalls, membership-only content, or account permissions.
- Do not automate spam-like behavior such as mass comments, mass follows, or mass likes.
- Default rate limits should be conservative.
- Write actions require explicit confirmation.
- The tool should only operate with user-owned accounts and user-authorized data.

## 13. First Build Recommendation

Although the target is a mature v1.0, development should still start with a stable core:

```bash
bili init
bili doctor
bili search
bili read
bili video info
bili comments
bili danmaku
bili login
bili status
```

After those are reliable, add:

```bash
bili download
bili user info
bili user videos
bili trending
bili live info
```

Only then add:

```bash
bili comment post
bili like
bili favorite
bili coin
bili publish
bili analytics
```

## 14. Reference Sources

Official references:

- Bilibili Open Platform: https://openhome.bilibili.com/doc
- Bilibili OAuth 2.0 introduction: https://open.bilibili.com/doc/4/eaf0e2b5-bde9-b9a0-9be1-019bb455701c
- Bilibili API signature/status docs: https://open.bilibili.com/doc/4/8673959e-f7bb-56e6-6e68-d225f971b81b
- Bilibili Live Open Platform: https://open-live.bilibili.com/
- Bilibili live access guide: https://bilibili.apifox.cn/doc-7499516

Ecosystem references:

- yt-dlp: https://github.com/yt-dlp/yt-dlp
- yt-dlp Bilibili extractor: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/bilibili.py
- biliup-rs: https://github.com/biliup/biliup-rs
- biliup: https://github.com/biliup/biliup
- public-clis/bilibili-cli: https://github.com/public-clis/bilibili-cli

Local reference:

- dy-cli repo: `/Users/xyh/Desktop/douyin`
