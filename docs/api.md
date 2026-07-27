# API Interface Reference

This document describes the Bilibili web/API interfaces currently used by `bilibili-cli`.

Important notes:

- These are Bilibili web endpoints observed and used by this CLI, not an official public API contract.
- Endpoint schemas, anti-risk behavior, signing requirements, and login requirements may change.
- Every CLI command should expose agent-friendly JSON with the envelope documented in [schema.md](schema.md).
- Write actions are dry-run by default at the CLI layer and require `--yes` for real execution.
- Expiring video/live stream URLs are hidden by default. Use `--show-urls` or `--show-url` only when raw URLs are needed.

## Common Transport

Base domains:

| Name | Base URL |
|---|---|
| Web | `https://www.bilibili.com` |
| Main API | `https://api.bilibili.com` |
| Live API | `https://api.live.bilibili.com` |
| Message API | `https://api.vc.bilibili.com` |

Default headers:

| Header | Value |
|---|---|
| `User-Agent` | Chrome-like desktop UA from `constants.DEFAULT_USER_AGENT` |
| `Accept` | `application/json, text/plain, */*` |
| `Accept-Language` | `zh-CN,zh;q=0.9,en;q=0.8` |
| `Referer` | Usually the matching Bilibili web page |
| `Origin` | `https://www.bilibili.com` |
| `Cookie` | Loaded from `~/.bili/cookies/<account>.json` when available |

Rate limiting:

- `BiliAPIClient` applies `rate_limit.request_delay` from local config before requests.
- Default delay is `0.5s` plus small random jitter.
- HTTP `429/500/502/503/504` are retried up to `api.retries`.
- Bilibili API code `-509`, `-799`, or HTTP `429` maps to `RATE_LIMITED`.

Risk/login/error mapping:

| Bilibili response | CLI error code | Retryable | Notes |
|---|---|---:|---|
| API code `-101` | `LOGIN_REQUIRED` | yes | Run `bili login` and retry |
| API code `-352`, `-412` or HTTP `403/412` | `CAPTCHA_REQUIRED` | yes | Open browser session or retry later |
| API code `-509`, `-799`, HTTP `429` | `RATE_LIMITED` | yes | Reduce request rate |
| API code `-404`, `62002` | `VIDEO_NOT_FOUND` | no | Resource unavailable |
| Invalid/changed JSON shape | `API_SCHEMA_CHANGED` | usually yes | Endpoint schema likely changed |

## Authentication And Signing

### Login State

`bili login` uses Playwright to open a headed Chromium browser and saves:

- Cookies: `~/.bili/cookies/<account>.json`
- Storage state: `~/.bili/storage_state/<account>.json`

`bili login --browser --browser-name chrome` imports Bilibili cookies from a local desktop browser through `browser-cookie3`.

### CSRF

Write endpoints require `bili_jct` from cookies. The client reads it through `csrf_token(account)` and verifies the session with `status()` before making a real write request.

### WBI Signing

`hot_search()` signs requests to `/x/web-interface/wbi/search/square`:

1. Read `/x/web-interface/nav`.
2. Extract `wbi_img.img_url` and `wbi_img.sub_url`.
3. Derive `img_key` and `sub_key`.
4. Mix keys with `MIXIN_KEY_ENC_TAB`.
5. Add `wts`.
6. Compute `w_rid = md5(urlencode(sorted(cleaned_params)) + mixin_key)`.

Implemented in `src/bili_cli/utils/wbi.py`.

## Endpoint Inventory

### Source Constant Index

This table maps source constants from `src/bili_cli/constants.py` to the endpoint or browser URL they represent.

| Constant | Endpoint / URL |
|---|---|
| `NAV_URL` | `https://api.bilibili.com/x/web-interface/nav` |
| `SEARCH_URL` | `https://api.bilibili.com/x/web-interface/search/type` |
| `VIDEO_VIEW_URL` | `https://api.bilibili.com/x/web-interface/view` |
| `VIDEO_TAGS_URL` | `https://api.bilibili.com/x/tag/archive/tags` |
| `VIDEO_RELATED_URL` | `https://api.bilibili.com/x/web-interface/archive/related` |
| `COMMENTS_MAIN_URL` | `https://api.bilibili.com/x/v2/reply/main` |
| `COMMENTS_REPLY_URL` | `https://api.bilibili.com/x/v2/reply/reply` |
| `POPULAR_URL` | `https://api.bilibili.com/x/web-interface/popular` |
| `RANKING_URL` | `https://api.bilibili.com/x/web-interface/ranking/v2` |
| `HOT_SEARCH_URL` | `https://api.bilibili.com/x/web-interface/wbi/search/square` |
| `DANMAKU_XML_URL` | `https://comment.bilibili.com/{cid}.xml` |
| `PLAYER_PLAYURL_URL` | `https://api.bilibili.com/x/player/playurl` |
| `USER_CARD_URL` | `https://api.bilibili.com/x/web-interface/card` |
| `SPACE_NAVNUM_URL` | `https://api.bilibili.com/x/space/navnum` |
| `SPACE_SETTING_URL` | `https://api.bilibili.com/x/space/setting` |
| `SPACE_ARC_SEARCH_URL` | `https://api.bilibili.com/x/space/arc/search` |
| `RELATION_STAT_URL` | `https://api.bilibili.com/x/relation/stat` |
| `RELATION_FOLLOWERS_URL` | `https://api.bilibili.com/x/relation/followers` |
| `RELATION_FOLLOWINGS_URL` | `https://api.bilibili.com/x/relation/followings` |
| `FAVORITE_CREATED_LIST_URL` | `https://api.bilibili.com/x/v3/fav/folder/created/list` |
| `FAVORITE_RESOURCE_LIST_URL` | `https://api.bilibili.com/x/v3/fav/resource/list` |
| `ARCHIVE_LIKE_URL` | `https://api.bilibili.com/x/web-interface/archive/like` |
| `COIN_ADD_URL` | `https://api.bilibili.com/x/web-interface/coin/add` |
| `FAVORITE_DEAL_URL` | `https://api.bilibili.com/x/v3/fav/resource/deal` |
| `WATCHLATER_ADD_URL` | `https://api.bilibili.com/x/v2/history/toview/add` |
| `RELATION_MODIFY_URL` | `https://api.bilibili.com/x/relation/modify` |
| `COMMENT_ADD_URL` | `https://api.bilibili.com/x/v2/reply/add` |
| `COMMENT_DELETE_URL` | `https://api.bilibili.com/x/v2/reply/del` |
| `LIVE_MAIN_LIST_URL` | `https://api.live.bilibili.com/xlive/web-interface/v1/webMain/getList` |
| `LIVE_ROOM_INFO_URL` | `https://api.live.bilibili.com/room/v1/Room/get_info` |
| `LIVE_ANCHOR_INFO_URL` | `https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room` |
| `LIVE_PLAY_INFO_URL` | `https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo` |
| `LIVE_DANMU_CONF_URL` | `https://api.live.bilibili.com/room/v1/Danmu/getConf` |
| `LIVE_DANMAKU_HISTORY_URL` | `https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory` |
| `CREATOR_HOME_URL` | `https://member.bilibili.com/platform/home` |
| `CREATOR_UPLOAD_URL` | `https://member.bilibili.com/platform/upload/video/frame` |
| `CREATOR_VIDEO_MANAGER_URL` | `https://member.bilibili.com/platform/upload-manager/article` |
| `MSGFEED_UNREAD_URL` | `https://api.bilibili.com/x/msgfeed/unread` |
| `VC_SESSION_LIST_URL` | `https://api.vc.bilibili.com/session_svr/v1/session_svr/get_sessions` |

### Account

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili status`, `bili me` / `status()` | GET | `/x/web-interface/nav` | optional | none | `is_login`, `mid`, `uname`, `vip_type`, `vip_status`, verification flags, `wallet` |
| `hot_search()` signing helper | GET | `/x/web-interface/nav` | optional | none | WBI keys under raw `data.wbi_img` |

### Search And Discovery

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili search` / `search()` | GET | `/x/web-interface/search/type` | optional | `search_type`, `keyword`, `page`, `page_size`, video `order` | `keyword`, `type`, `page`, `limit`, `total`, `items[]` |
| `bili trending` / `trending(source=popular)` | GET | `/x/web-interface/popular` | optional | `ps`, `pn` | `source=popular`, `items[]` video cards |
| `bili ranking`, `bili rank` / `trending(source=ranking)` | GET | `/x/web-interface/ranking/v2` | optional | `rid`, `type=all` | `source=ranking`, `rid`, `items[]` video cards |
| `bili hot-search`, `bili hs` / `hot_search()` | GET | `/x/web-interface/wbi/search/square` | optional, WBI signed | `platform=web`, `limit`, `wts`, `w_rid` | `title`, `trackid`, `items[]` hot words |

Search type mapping:

| CLI type | API `search_type` |
|---|---|
| `video` | `video` |
| `user` | `bili_user` |
| `live` | `live` |
| `article` | `article` |
| `bangumi` | `media_bangumi` |

Video order mapping:

| CLI order | API `order` |
|---|---|
| `default` | `totalrank` |
| `views` | `click` |
| `new` | `pubdate` |
| `danmaku` | `dm` |
| `favorite` | `stow` |

Browser fallback:

- `search --browser-fallback` uses Playwright to load `https://search.bilibili.com/video?keyword=<keyword>` and extracts `BV...` links from the DOM.
- `ranking` uses API first and can fall back to a Playwright browser fetch when the public API returns a risk response.

### Video

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili detail`, `bili read`, `bili video info` / `video_detail()` | GET | `/x/web-interface/view` | optional | `bvid` or `aid` | Raw video detail plus `url` |
| `bili video tags` / `video_tags()` | GET | `/x/tag/archive/tags` | optional | `bvid`, `aid` | Raw tag list |
| `bili video related` / `video_related()` | GET | `/x/web-interface/archive/related` | optional | `bvid`, `aid` | Raw related video list, truncated to `limit` |
| `bili download` / `playurl()` | GET | `/x/player/playurl` | optional, higher quality may require login | `bvid`, `cid`, `qn`, `fnval=4048`, `fourk=1` | `dash`, `durl`, quality metadata |
| `bili danmaku` / `danmaku()` | GET | `https://comment.bilibili.com/{cid}.xml` | optional | path `cid` | Parsed danmaku items |

Supported quality aliases:

| Alias | `qn` |
|---|---:|
| `360p` | 16 |
| `480p` | 32 |
| `720p` | 64 |
| `1080p` | 80 |
| `1080p+` | 112 |
| `1080p60` | 116 |
| `4k` | 120 |
| `hdr` | 125 |
| `dolby` | 126 |
| `8k` | 127 |
| `best` | 127 |

Download stream behavior:

- DASH responses are split into video and audio streams.
- DURL responses are treated as video-only.
- `streams` in JSON is a public plan by default: it contains `url_present` and `backup_url_count`, not raw URLs.
- `--show-urls` includes expiring media URLs.
- Internal `_private_streams` is never printed in public JSON output.

### Comments

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili comments`, `bili video comments` / `comments()` | GET | `/x/v2/reply/main` | optional, may be risk-limited | `type=1`, `oid=<aid>`, `mode`, `ps`, `pagination_str` | `video`, `total`, `comments[]` |
| `bili comments --replies-to` / `comments(replies_to=...)` | GET | `/x/v2/reply/reply` | optional, may be risk-limited | `type=1`, `oid=<aid>`, `root`, `pn=1`, `ps` | `video`, `total`, replies in `comments[]` |
| `bili comment post` / `comment_post()` | POST | `/x/v2/reply/add` | required | `type=1`, `oid=<aid>`, `message`, optional `root`, `parent`, `csrf` | `action`, `video`, normalized `reply` |
| `bili comment delete` / `comment_delete()` | POST | `/x/v2/reply/del` | required | `type=1`, `oid=<aid>`, `rpid`, `csrf` | `action`, `video`, `rpid`, raw `data` |

Comment sort mapping:

| CLI sort | API `mode` |
|---|---:|
| `hot` | 3 |
| `new` | 2 |

Normalized comment item:

```json
{
  "rpid": "...",
  "oid": "...",
  "mid": "...",
  "ctime": 0,
  "like": 0,
  "reply_count": 0,
  "message": "...",
  "member": {
    "mid": "...",
    "uname": "...",
    "avatar": "...",
    "level": 0,
    "vip_status": 0
  }
}
```

### User And Space

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili user info`, `bili profile` / `user_info()` | GET | `/x/web-interface/card` | optional | `mid` | Basic profile card |
| `user_info()` optional enrichment | GET | `/x/relation/stat` | optional | `vmid` | Following/follower stats |
| `user_info()` optional enrichment | GET | `/x/space/navnum` | optional | `mid` | Space content counts |
| `user_info()` optional enrichment | GET | `/x/space/setting` | optional | `mid` | Privacy settings |
| `bili user videos`, `bili profile --videos`, `bili creator videos` / `user_videos()` | GET | `/x/space/arc/search` | optional, frequently rate-limited | `mid`, `pn`, `ps`, `order` | `mid`, `page`, `limit`, `total`, `items[]` |
| `bili user following` / `user_following()` | GET | `/x/relation/followings` | optional, privacy/risk-limited | `vmid`, `pn`, `ps`, `order_type=attention` | Relation users |
| `bili user followers` / `user_followers()` | GET | `/x/relation/followers` | optional, privacy/risk-limited | `vmid`, `pn`, `ps`, `order_type=attention` | Relation users |
| `bili user favorites`, `bili favorite folders` / `user_favorites()` | GET | `/x/v3/fav/folder/created/list` | optional for public, required for own private listing | `up_mid`, `pn`, `ps` | Favorite folder list |
| `bili favorite items`, `bili favorite list` / `favorite_resources()` | GET | `/x/v3/fav/resource/list` | optional for public folders, login may be required for private folders | `media_id`, `pn`, `ps`, `keyword`, `order`, `type` | Favorite folder metadata and media items |

`favorite_folders()` first calls `status()` and then lists folders for the current login MID.

### Favorite And Social Write Actions

All of these are real POST interfaces in `BiliAPIClient`. The CLI command layer defaults to dry-run and calls them only when `--yes` is provided.

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili like` / `like_video()` | POST | `/x/web-interface/archive/like` | required | `aid`, `like=1` or `2`, `csrf` | `action`, `video`, raw `data` |
| `bili coin` / `coin_video()` | POST | `/x/web-interface/coin/add` | required | `aid`, `multiply=1..2`, `select_like`, `csrf` | `action`, `video`, raw `data` |
| `bili favorite add/remove` / `favorite_video()` | POST | `/x/v3/fav/resource/deal` | required | `rid=<aid>`, `type=2`, `add_media_ids` or `del_media_ids`, `csrf` | `action`, `video`, `folder_id`, raw `data` |
| `bili watchlater add` / `watchlater_add()` | POST | `/x/v2/history/toview/add` | required | `aid`, `csrf` | `action`, `video`, raw `data` |
| `bili follow/unfollow` / `follow_user()` | POST | `/x/relation/modify` | required | `fid`, `act=1` or `2`, `re_src=11`, `csrf` | `action`, `mid`, raw `data` |

### Live

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili live list` / `live_list(keyword=None)` | GET | `/xlive/web-interface/v1/webMain/getList` | optional | `platform=web` | Recommended live rooms |
| `bili live list --keyword` / `live_list(keyword=...)` | GET | `/x/web-interface/search/type` | optional | `search_type=live`, `keyword`, `page`, `page_size` | Normalized live search results |
| `bili live info` / `_live_room_info()` | GET | `/room/v1/Room/get_info` | optional | `room_id` | Room metadata |
| `bili live info` enrichment | GET | `/live_user/v1/UserInfo/get_anchor_in_room` | optional | `roomid` | Anchor metadata |
| `bili live info`, `bili live streams`, `bili live record` / `live_streams()` | GET | `/xlive/web-room/v2/index/getRoomPlayInfo` | optional | `room_id`, `protocol=0,1`, `format=0,1,2`, `codec=0,1`, `qn=10000`, `platform=web`, `ptype=8` | Stream variants and quality descriptions |
| `bili live danmaku` / `live_danmaku()` | GET | `/xlive/web-room/v1/dM/gethistory` | optional | `roomid` | Recent room/admin danmaku |
| `bili live danmaku-conf` / `live_danmaku_conf()` | GET | `/room/v1/Danmu/getConf` | optional | `room_id`, `platform=pc`, `player=web` | Host list and `token_present` |

Live stream JSON:

- Hidden mode: exposes `protocol`, `format`, `codec`, `current_qn`, `accept_qn`, `url_present`, `url_count`.
- URL mode: adds `url` and `urls`.
- `live record` internally reads stream URLs but hides them unless `--show-url` is provided.
- Danmaku config never prints the token, only `token_present`.

### Notifications And Messages

| CLI / client method | Method | Endpoint | Auth | Params | Normalized output |
|---|---|---|---|---|---|
| `bili notifications` / `notifications()` | GET | `/x/msgfeed/unread` | required | none | `counts`, `raw` |
| `bili messages` / `messages()` | GET | `https://api.vc.bilibili.com/session_svr/v1/session_svr/get_sessions` | required | `session_type=1`, `platform=web` | `items[]`, `total` |

Normalized message session:

```json
{
  "type": "message_session",
  "talker_id": 0,
  "nickname": "...",
  "unread": 0,
  "last_text": "...",
  "session_ts": 0
}
```

### Creator And Publish Browser URLs

These are browser handoff URLs, not JSON API endpoints in the current implementation.

| CLI command | URL | Behavior |
|---|---|---|
| `bili creator open --page home` | `https://member.bilibili.com/platform/home` | Opens creator center |
| `bili creator open --page upload` | `https://member.bilibili.com/platform/upload/video/frame` | Opens upload page |
| `bili creator open --page manager` | `https://member.bilibili.com/platform/upload-manager/article` | Opens manager page |
| `bili publish --yes` | `https://member.bilibili.com/platform/upload/video/frame` | Browser handoff with local file path |
| `bili creator delete --yes` | `https://member.bilibili.com/platform/upload-manager/article` | Browser handoff for manual delete |

`bili publish` without `--yes` only creates a local task under `~/.bili/logs/publish/`.

## Command To API Mapping

| Command | API client methods / helpers |
|---|---|
| `bili login` | Playwright browser, cookie/storage save |
| `bili login --browser` | `browser-cookie3`, cookie import |
| `bili status`, `bili me` | `status()` |
| `bili search` | `search()` or Playwright `browser_search()` fallback |
| `bili read`, `bili detail` | Last-result index + `video_detail()` |
| `bili video info` | `video_detail()` |
| `bili video pages` | `video_detail()` |
| `bili video tags` | `video_tags()` |
| `bili video related` | `video_related()` |
| `bili comments`, `bili video comments` | `comments()` |
| `bili danmaku` | `danmaku()` |
| `bili download` | `video_detail()`, `playurl()`, stream selector, local downloader |
| `bili trending` | `trending(source=popular)` |
| `bili ranking`, `bili rank` | `trending(source=ranking)` or Playwright `browser_ranking()` fallback |
| `bili hot-search`, `bili hs` | `hot_search()` |
| `bili user info` | `user_info()` |
| `bili user videos` | `user_videos()` |
| `bili user followers` | `user_followers()` |
| `bili user following` | `user_following()` |
| `bili user favorites` | `user_favorites()` |
| `bili profile` | `user_info()` plus optional section methods |
| `bili favorite folders` | `favorite_folders()` |
| `bili favorite items`, `bili favorite list` | `favorite_resources()` |
| `bili like` | dry-run plan or `like_video()` with `--yes` |
| `bili coin` | dry-run plan or `coin_video()` with `--yes` |
| `bili favorite add/remove` | dry-run plan or `favorite_video()` with `--yes` |
| `bili watchlater add` | dry-run plan or `watchlater_add()` with `--yes` |
| `bili follow` | dry-run plan or `follow_user()` with `--yes` |
| `bili comment post/delete` | dry-run plan or `comment_post()` / `comment_delete()` with `--yes` |
| `bili live list` | `live_list()` |
| `bili live info` | `live_info()` |
| `bili live streams` | `live_streams()` |
| `bili live danmaku` | `live_danmaku()` |
| `bili live danmaku-conf` | `live_danmaku_conf()` |
| `bili live record` | `live_info(show_urls=True)`, stream selector, `ffmpeg` recorder |
| `bili publish` | Local publish task, optional browser handoff |
| `bili creator videos` | `status()` then `user_videos(current_mid)` |
| `bili creator delete` | dry-run plan or browser handoff |
| `bili analytics --video` | `video_detail()`, `video_tags()`, `video_related()`, `comments()` |
| `bili analytics` | Local cache/task summary |
| `bili notifications` | `notifications()` |
| `bili messages` | `messages()` |

## Known Operational Limits

- `x/space/arc/search` can return `RATE_LIMITED` during repeated tests, especially for `creator videos` or repeated `user videos`.
- Comment, ranking, search, and live APIs can return captcha/risk responses depending on traffic and login state.
- Higher-quality media URLs may require a valid login session and still expire quickly.
- Some user relation/favorite data depends on the target user's privacy settings.
- Real write actions should be used sparingly and always with clear user confirmation.

## Last Verified

Manual E2E status as of 2026-07-28:

- Logged-in account: `村口修鞋师傅`
- Unit/contract tests: `39 passed`
- Logged-in E2E: `51` checks, `50` passed, `0` hard failures
- One soft failure: `creator videos` returned `RATE_LIMITED`
- Headed browser search/ranking adapters passed
