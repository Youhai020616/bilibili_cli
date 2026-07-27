"""Bilibili web API client."""

from __future__ import annotations

import html
import json
import random
import re
import time
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from bili_cli import constants
from bili_cli.config import load_config
from bili_cli.errors import APIError, BiliError, CaptchaRequiredError, map_api_code
from bili_cli.session import account_name, cookie_header
from bili_cli.utils.ids import VideoRef, parse_video_ref, video_url


class BiliAPIClient:
    """Thin Bilibili web API client with normalized high-level methods."""

    def __init__(
        self,
        *,
        account: str | None = None,
        timeout: int = 30,
        proxy: str = "",
        request_delay: float = 0.5,
        retries: int = 3,
    ):
        self.account = account_name(account)
        self.timeout = timeout
        self.proxy = proxy
        self.request_delay = request_delay
        self.retries = retries
        self._client: httpx.Client | None = None
        self._last_request_time = 0.0

    @classmethod
    def from_config(cls, account: str | None = None) -> "BiliAPIClient":
        cfg = load_config()
        return cls(
            account=account,
            timeout=int(cfg.get("api", {}).get("timeout", 30)),
            proxy=str(cfg.get("api", {}).get("proxy") or ""),
            request_delay=float(cfg.get("rate_limit", {}).get("request_delay", 0.5)),
            retries=int(cfg.get("api", {}).get("retries", 3)),
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            transport_kwargs: dict[str, Any] = {}
            if self.proxy:
                transport_kwargs["proxy"] = self.proxy
            headers = {
                "User-Agent": constants.DEFAULT_USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": constants.BILI_DOMAIN + "/",
                "Origin": constants.BILI_DOMAIN,
            }
            cookies = cookie_header(self.account)
            if cookies:
                headers["Cookie"] = cookies
            self._client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers=headers,
                **transport_kwargs,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _delay(self) -> None:
        if self.request_delay <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed + random.uniform(0, 0.2))

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(max(1, self.retries)):
            self._delay()
            try:
                resp = self.client.get(url, params=params, headers=headers)
                self._last_request_time = time.time()
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(2**attempt)
                    continue
                raise APIError(str(exc), "NETWORK_ERROR", True) from exc

            if resp.status_code in {403, 412}:
                raise CaptchaRequiredError(f"HTTP {resp.status_code} risk verification response")
            if resp.status_code in {429, 500, 502, 503, 504} and attempt + 1 < self.retries:
                time.sleep(2**attempt + random.uniform(0, 0.5))
                continue

            text = resp.text.lstrip()
            if text.startswith("<!DOCTYPE html") or text.startswith("<html"):
                raise CaptchaRequiredError("HTML response returned instead of JSON")
            try:
                payload = resp.json()
            except ValueError as exc:
                raise APIError("Invalid JSON response", "API_SCHEMA_CHANGED", True) from exc

            if isinstance(payload, dict) and payload.get("code", 0) != 0:
                api_code = int(payload.get("code") or 0)
                message = str(payload.get("message") or payload.get("msg") or "")
                raise map_api_code(api_code, message)
            if not isinstance(payload, dict):
                raise APIError("Unexpected API response type", "API_SCHEMA_CHANGED", True)
            return payload

        raise APIError(str(last_error or "Request failed"), "NETWORK_ERROR", True)

    def status(self) -> dict[str, Any]:
        try:
            resp = self.client.get(constants.NAV_URL)
            payload = resp.json()
        except Exception as exc:
            raise APIError("Unable to read login status", "NETWORK_ERROR", True) from exc
        code = int(payload.get("code") or 0)
        if code == -101:
            return {
                "is_login": False,
                "mid": None,
                "uname": None,
                "vip_type": None,
                "vip_status": None,
                "email_verified": None,
                "mobile_verified": None,
                "wallet": None,
            }
        if code != 0:
            message = str(payload.get("message") or payload.get("msg") or "")
            raise map_api_code(code, message)
        data = payload.get("data") or {}
        return {
            "is_login": bool(data.get("isLogin")),
            "mid": data.get("mid"),
            "uname": data.get("uname"),
            "vip_type": data.get("vipType"),
            "vip_status": data.get("vipStatus"),
            "email_verified": data.get("email_verified"),
            "mobile_verified": data.get("mobile_verified"),
            "wallet": data.get("wallet"),
        }

    def search(
        self,
        *,
        keyword: str,
        search_type: str = "video",
        limit: int = 20,
        page: int = 1,
        order: str = "default",
    ) -> dict[str, Any]:
        api_type = constants.SEARCH_TYPE_MAP.get(search_type, search_type)
        params = {
            "search_type": api_type,
            "keyword": keyword,
            "page": page,
            "page_size": min(max(limit, 1), 50),
        }
        if search_type == "video":
            params["order"] = constants.SEARCH_ORDER_MAP.get(order, "totalrank")
        payload = self.get_json(
            constants.SEARCH_URL,
            params=params,
            headers={"Referer": "https://search.bilibili.com/"},
        )
        data = payload.get("data") or {}
        raw_items = data.get("result") or []
        items = [_normalize_search_item(item, search_type) for item in raw_items[:limit]]
        return {
            "keyword": keyword,
            "type": search_type,
            "page": page,
            "limit": limit,
            "total": data.get("numResults") or data.get("num_results"),
            "items": items,
        }

    def video_detail(self, video_id: str) -> dict[str, Any]:
        ref = parse_video_ref(video_id)
        payload = self.get_json(constants.VIDEO_VIEW_URL, params=_video_params(ref))
        data = payload.get("data") or {}
        if not data:
            raise APIError("Empty video detail response", "API_SCHEMA_CHANGED", True)
        data["url"] = video_url(data.get("bvid"), data.get("aid"))
        return data

    def video_tags(self, video_id: str) -> list[dict[str, Any]]:
        detail = self.video_detail(video_id)
        payload = self.get_json(constants.VIDEO_TAGS_URL, params={"bvid": detail.get("bvid"), "aid": detail.get("aid")})
        return list(payload.get("data") or [])

    def video_related(self, video_id: str, limit: int = 10) -> list[dict[str, Any]]:
        detail = self.video_detail(video_id)
        payload = self.get_json(constants.VIDEO_RELATED_URL, params={"bvid": detail.get("bvid"), "aid": detail.get("aid")})
        return list(payload.get("data") or [])[:limit]

    def comments(
        self,
        video_id: str,
        *,
        count: int = 20,
        sort: str = "hot",
        replies_to: str | None = None,
    ) -> dict[str, Any]:
        detail = self.video_detail(video_id)
        aid = detail.get("aid")
        if replies_to:
            params = {
                "type": 1,
                "oid": aid,
                "root": replies_to,
                "pn": 1,
                "ps": min(max(count, 1), 50),
            }
            payload = self.get_json(
                constants.COMMENTS_REPLY_URL,
                params=params,
                headers={"Referer": video_url(detail.get("bvid"), aid)},
            )
            data = payload.get("data") or {}
            replies = [_normalize_comment(item) for item in data.get("replies") or []]
            return {"video": _video_summary(detail), "total": data.get("page", {}).get("count"), "comments": replies[:count]}

        comments: list[dict[str, Any]] = []
        offset = ""
        total: int | None = None
        while len(comments) < count:
            pagination_str = json.dumps({"offset": offset}, separators=(",", ":"))
            params = {
                "type": 1,
                "oid": aid,
                "mode": constants.COMMENT_SORT_MODE.get(sort, 3),
                "ps": min(max(count - len(comments), 1), 20),
                "pagination_str": pagination_str,
            }
            payload = self.get_json(
                constants.COMMENTS_MAIN_URL,
                params=params,
                headers={"Referer": video_url(detail.get("bvid"), aid)},
            )
            data = payload.get("data") or {}
            cursor = data.get("cursor") or {}
            if total is None:
                total = cursor.get("all_count")
            batch = data.get("replies") or []
            comments.extend(_normalize_comment(item) for item in batch)
            next_offset = (cursor.get("pagination_reply") or {}).get("next_offset") or ""
            if not next_offset or cursor.get("is_end") or not batch:
                break
            offset = next_offset

        return {"video": _video_summary(detail), "total": total, "comments": comments[:count]}

    def danmaku(self, video_id: str, *, page: int = 1) -> dict[str, Any]:
        detail = self.video_detail(video_id)
        pages = detail.get("pages") or []
        if not pages:
            raise APIError("Video has no pages/cid data", "API_SCHEMA_CHANGED", True)
        if page < 1 or page > len(pages):
            raise APIError(f"Page out of range: {page}", "UNSUPPORTED_INPUT")
        page_data = pages[page - 1]
        cid = page_data.get("cid")
        if not cid:
            raise APIError("Missing cid for selected page", "API_SCHEMA_CHANGED", True)

        url = constants.DANMAKU_XML_URL.format(cid=cid)
        resp = self.client.get(url, headers={"Accept": "application/xml,text/xml,*/*", "Referer": video_url(detail.get("bvid"), detail.get("aid"))})
        if resp.status_code in {403, 412}:
            raise CaptchaRequiredError(f"HTTP {resp.status_code} risk verification response")
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            raise APIError("Invalid danmaku XML response", "API_SCHEMA_CHANGED", True) from exc
        items = []
        for node in root.findall("d"):
            attrs = (node.attrib.get("p") or "").split(",")
            items.append(
                {
                    "time": float(attrs[0]) if len(attrs) > 0 and attrs[0] else 0.0,
                    "mode": int(attrs[1]) if len(attrs) > 1 and attrs[1] else 0,
                    "size": int(attrs[2]) if len(attrs) > 2 and attrs[2] else 0,
                    "color": int(attrs[3]) if len(attrs) > 3 and attrs[3] else 0,
                    "timestamp": int(attrs[4]) if len(attrs) > 4 and attrs[4] else 0,
                    "pool": int(attrs[5]) if len(attrs) > 5 and attrs[5] else 0,
                    "user_hash": attrs[6] if len(attrs) > 6 else "",
                    "id": attrs[7] if len(attrs) > 7 else "",
                    "text": html.unescape(node.text or ""),
                }
            )
        return {"video": _video_summary(detail), "page": page, "cid": cid, "items": items}

    def trending(self, *, count: int = 20, source: str = "popular", rid: int = 0) -> dict[str, Any]:
        if source == "ranking":
            payload = self.get_json(constants.RANKING_URL, params={"rid": rid, "type": "all"})
            raw_items = (payload.get("data") or {}).get("list") or []
        else:
            payload = self.get_json(constants.POPULAR_URL, params={"ps": min(max(count, 1), 50), "pn": 1})
            raw_items = (payload.get("data") or {}).get("list") or []
        items = [_normalize_video_card(item) for item in list(raw_items)[:count]]
        return {"source": source, "rid": rid, "items": items}


def _video_params(ref: VideoRef) -> dict[str, Any]:
    if ref.bvid:
        return {"bvid": ref.bvid}
    if ref.aid is not None:
        return {"aid": ref.aid}
    return {"bvid": ref.raw}


def _normalize_search_item(item: dict[str, Any], search_type: str) -> dict[str, Any]:
    if search_type == "user":
        mid = item.get("mid")
        return {
            "type": "user",
            "mid": mid,
            "name": _clean(item.get("uname")),
            "uname": _clean(item.get("uname")),
            "fans": item.get("fans"),
            "videos": item.get("videos"),
            "sign": _clean(item.get("usign")),
            "avatar": item.get("upic"),
            "url": f"https://space.bilibili.com/{mid}" if mid else "",
        }
    if search_type == "live":
        room_id = item.get("roomid") or item.get("room_id")
        uid = item.get("uid")
        return {
            "type": "live",
            "id": room_id,
            "room_id": room_id,
            "mid": uid,
            "title": _clean(item.get("title")),
            "author": _clean(item.get("uname")),
            "online": item.get("online"),
            "cover": item.get("cover") or item.get("uface"),
            "url": f"https://live.bilibili.com/{room_id}" if room_id else "",
        }
    bvid = item.get("bvid")
    aid = item.get("aid")
    return {
        "type": "video",
        "bvid": bvid,
        "aid": aid,
        "title": _clean(item.get("title")),
        "author": _clean(item.get("author") or item.get("uname")),
        "mid": item.get("mid"),
        "play": item.get("play"),
        "danmaku": item.get("danmaku"),
        "duration": item.get("duration"),
        "description": _clean(item.get("description")),
        "pic": item.get("pic"),
        "pubdate": item.get("pubdate"),
        "typename": item.get("typename"),
        "url": item.get("arcurl") or video_url(bvid, aid),
    }


def _normalize_video_card(item: dict[str, Any]) -> dict[str, Any]:
    owner = item.get("owner") or {}
    stat = item.get("stat") or {}
    return {
        "type": "video",
        "bvid": item.get("bvid"),
        "aid": item.get("aid"),
        "cid": item.get("cid"),
        "title": _clean(item.get("title")),
        "desc": _clean(item.get("desc")),
        "duration": item.get("duration"),
        "pubdate": item.get("pubdate"),
        "pic": item.get("pic"),
        "tname": item.get("tname") or item.get("tnamev2"),
        "owner": {
            "mid": owner.get("mid"),
            "name": owner.get("name"),
            "face": owner.get("face"),
        },
        "stat": {
            "view": stat.get("view") or stat.get("vv"),
            "danmaku": stat.get("danmaku"),
            "reply": stat.get("reply"),
            "favorite": stat.get("favorite"),
            "coin": stat.get("coin"),
            "share": stat.get("share"),
            "like": stat.get("like"),
        },
        "url": video_url(item.get("bvid"), item.get("aid")),
    }


def _normalize_comment(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content") or {}
    member = item.get("member") or {}
    return {
        "rpid": item.get("rpid_str") or item.get("rpid"),
        "oid": item.get("oid_str") or item.get("oid"),
        "mid": item.get("mid_str") or item.get("mid"),
        "ctime": item.get("ctime"),
        "like": item.get("like"),
        "reply_count": item.get("rcount") or item.get("count") or 0,
        "message": content.get("message") or "",
        "member": {
            "mid": member.get("mid"),
            "uname": member.get("uname"),
            "avatar": member.get("avatar"),
            "level": (member.get("level_info") or {}).get("current_level"),
            "vip_status": (member.get("vip") or {}).get("vipStatus"),
        },
    }


def _video_summary(detail: dict[str, Any]) -> dict[str, Any]:
    owner = detail.get("owner") or {}
    return {
        "bvid": detail.get("bvid"),
        "aid": detail.get("aid"),
        "title": detail.get("title"),
        "owner": {"mid": owner.get("mid"), "name": owner.get("name")},
        "url": video_url(detail.get("bvid"), detail.get("aid")),
    }


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", "", str(value))
    return html.unescape(text).strip()
