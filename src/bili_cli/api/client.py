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
from bili_cli.errors import APIError, BiliError, CaptchaRequiredError, LoginRequiredError, map_api_code
from bili_cli.session import account_name, cookie_header, csrf_token
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

    def post_json(
        self,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(max(1, self.retries)):
            self._delay()
            try:
                resp = self.client.post(url, data=data, headers=headers)
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

    def playurl(
        self,
        video_id: str,
        *,
        cid: int | None = None,
        quality: str | int = "best",
        page: int = 1,
        fnval: int = 4048,
    ) -> dict[str, Any]:
        detail = self.video_detail(video_id)
        pages = detail.get("pages") or []
        if cid is None:
            if page < 1 or page > len(pages):
                raise APIError(f"Page out of range: {page}", "UNSUPPORTED_INPUT")
            cid = pages[page - 1].get("cid")
        if not cid:
            raise APIError("Missing cid for selected page", "API_SCHEMA_CHANGED", True)

        params = {
            "bvid": detail.get("bvid"),
            "cid": cid,
            "qn": _quality_to_qn(quality),
            "fnval": fnval,
            "fourk": 1,
        }
        payload = self.get_json(
            constants.PLAYER_PLAYURL_URL,
            params=params,
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        data = payload.get("data") or {}
        return {
            "video": _video_summary(detail),
            "page": page,
            "cid": cid,
            "requested_quality": quality,
            "actual_quality": data.get("quality"),
            "accept_quality": data.get("accept_quality") or [],
            "accept_description": data.get("accept_description") or [],
            "timelength": data.get("timelength"),
            "format": data.get("format"),
            "dash": data.get("dash"),
            "durl": data.get("durl"),
        }

    def trending(self, *, count: int = 20, source: str = "popular", rid: int = 0) -> dict[str, Any]:
        if source == "ranking":
            payload = self.get_json(constants.RANKING_URL, params={"rid": rid, "type": "all"})
            raw_items = (payload.get("data") or {}).get("list") or []
        else:
            payload = self.get_json(constants.POPULAR_URL, params={"ps": min(max(count, 1), 50), "pn": 1})
            raw_items = (payload.get("data") or {}).get("list") or []
        items = [_normalize_video_card(item) for item in list(raw_items)[:count]]
        return {"source": source, "rid": rid, "items": items}

    def live_list(self, *, keyword: str | None = None, count: int = 20, page: int = 1) -> dict[str, Any]:
        if keyword:
            result = self.search(keyword=keyword, search_type="live", limit=count, page=page)
            result["items"] = [_normalize_live_search_item(item) for item in result.get("items") or []]
            return result
        payload = self.get_json(
            constants.LIVE_MAIN_LIST_URL,
            params={"platform": "web"},
            headers={"Referer": "https://live.bilibili.com/"},
        )
        data = payload.get("data") or {}
        raw_items = data.get("recommend_room_list") or []
        return {
            "keyword": None,
            "page": 1,
            "limit": count,
            "online_total": data.get("online_total"),
            "dynamic": data.get("dynamic"),
            "items": [_normalize_live_room_card(item) for item in raw_items[:count]],
        }

    def live_info(self, room_id: str | int, *, show_urls: bool = False) -> dict[str, Any]:
        room = self._live_room_info(room_id)
        anchor = self._optional_data(
            constants.LIVE_ANCHOR_INFO_URL,
            params={"roomid": room.get("room_id") or room_id},
            headers={"Referer": f"https://live.bilibili.com/{room_id}"},
        )
        play = self._optional_data(
            constants.LIVE_PLAY_INFO_URL,
            params=_live_play_params(room.get("room_id") or room_id),
            headers={"Referer": f"https://live.bilibili.com/{room_id}"},
        )
        return _normalize_live_info(room, anchor=anchor, play=play, show_urls=show_urls)

    def live_streams(self, room_id: str | int, *, show_urls: bool = False) -> dict[str, Any]:
        room = self._live_room_info(room_id)
        play = self.get_json(
            constants.LIVE_PLAY_INFO_URL,
            params=_live_play_params(room.get("room_id") or room_id),
            headers={"Referer": f"https://live.bilibili.com/{room_id}"},
        ).get("data") or {}
        return {
            "room_id": str(room.get("room_id") or room_id),
            "short_id": room.get("short_id"),
            "live_status": room.get("live_status"),
            "is_live": room.get("live_status") == 1,
            "streams": _extract_live_streams(play, show_urls=show_urls),
            "qualities": _live_quality_desc(play),
        }

    def live_danmaku(self, room_id: str | int, *, count: int = 20) -> dict[str, Any]:
        room = self._live_room_info(room_id)
        payload = self.get_json(
            constants.LIVE_DANMAKU_HISTORY_URL,
            params={"roomid": room.get("room_id") or room_id},
            headers={"Referer": f"https://live.bilibili.com/{room_id}"},
        )
        data = payload.get("data") or {}
        items = [_normalize_live_danmaku(item) for item in (data.get("room") or [])]
        admin_items = [_normalize_live_danmaku(item) for item in (data.get("admin") or [])]
        return {
            "room_id": str(room.get("room_id") or room_id),
            "short_id": room.get("short_id"),
            "live_status": room.get("live_status"),
            "is_live": room.get("live_status") == 1,
            "items": (admin_items + items)[: max(count, 0)],
        }

    def live_danmaku_conf(self, room_id: str | int) -> dict[str, Any]:
        room = self._live_room_info(room_id)
        payload = self.get_json(
            constants.LIVE_DANMU_CONF_URL,
            params={"room_id": room.get("room_id") or room_id, "platform": "pc", "player": "web"},
            headers={"Referer": f"https://live.bilibili.com/{room_id}"},
        )
        data = payload.get("data") or {}
        hosts = data.get("host_server_list") or data.get("server_list") or []
        return {
            "room_id": str(room.get("room_id") or room_id),
            "host": data.get("host"),
            "port": data.get("port"),
            "token_present": bool(data.get("token")),
            "hosts": [
                {
                    "host": item.get("host"),
                    "port": item.get("port"),
                    "ws_port": item.get("ws_port"),
                    "wss_port": item.get("wss_port"),
                }
                for item in hosts
            ],
        }

    def _live_room_info(self, room_id: str | int) -> dict[str, Any]:
        payload = self.get_json(
            constants.LIVE_ROOM_INFO_URL,
            params={"room_id": room_id},
            headers={"Referer": f"https://live.bilibili.com/{room_id}"},
        )
        data = payload.get("data") or {}
        if not data:
            raise APIError("Empty live room response", "API_SCHEMA_CHANGED", True)
        return data

    def user_info(self, mid: str | int) -> dict[str, Any]:
        user_mid = _normalize_mid(mid)
        referer = f"https://space.bilibili.com/{user_mid}/"
        card_payload = self.get_json(constants.USER_CARD_URL, params={"mid": user_mid}, headers={"Referer": referer})
        card_data = card_payload.get("data") or {}
        if not card_data.get("card"):
            raise APIError("Empty user card response", "API_SCHEMA_CHANGED", True)
        relation = self._optional_data(constants.RELATION_STAT_URL, params={"vmid": user_mid}, headers={"Referer": referer})
        navnum = self._optional_data(constants.SPACE_NAVNUM_URL, params={"mid": user_mid}, headers={"Referer": referer})
        setting = self._optional_data(constants.SPACE_SETTING_URL, params={"mid": user_mid}, headers={"Referer": referer})
        return _normalize_user_info(card_data, relation=relation, navnum=navnum, setting=setting, mid=user_mid)

    def user_videos(
        self,
        mid: str | int,
        *,
        limit: int = 20,
        page: int = 1,
        order: str = "pubdate",
    ) -> dict[str, Any]:
        user_mid = _normalize_mid(mid)
        params = {
            "mid": user_mid,
            "pn": max(page, 1),
            "ps": min(max(limit, 1), 50),
            "order": order,
        }
        payload = self.get_json(
            constants.SPACE_ARC_SEARCH_URL,
            params=params,
            headers={"Referer": f"https://space.bilibili.com/{user_mid}/video"},
        )
        data = payload.get("data") or {}
        list_data = data.get("list") or {}
        page_data = data.get("page") or {}
        raw_items = list_data.get("vlist") or []
        return {
            "mid": str(user_mid),
            "page": max(page, 1),
            "limit": limit,
            "total": page_data.get("count"),
            "items": [_normalize_space_video(item) for item in raw_items[:limit]],
        }

    def user_following(self, mid: str | int, *, limit: int = 20, page: int = 1) -> dict[str, Any]:
        return self._relation_list(mid, relation="following", limit=limit, page=page)

    def user_followers(self, mid: str | int, *, limit: int = 20, page: int = 1) -> dict[str, Any]:
        return self._relation_list(mid, relation="followers", limit=limit, page=page)

    def user_favorites(self, mid: str | int, *, limit: int = 20, page: int = 1) -> dict[str, Any]:
        user_mid = _normalize_mid(mid)
        params = {"up_mid": user_mid, "pn": max(page, 1), "ps": min(max(limit, 1), 50)}
        payload = self.get_json(
            constants.FAVORITE_CREATED_LIST_URL,
            params=params,
            headers={"Referer": f"https://space.bilibili.com/{user_mid}/favlist"},
        )
        data = payload.get("data") or {}
        raw_items = data.get("list") or []
        return {
            "mid": str(user_mid),
            "page": max(page, 1),
            "limit": limit,
            "total": data.get("count"),
            "has_more": bool(data.get("has_more")),
            "items": [_normalize_favorite_folder(item) for item in raw_items[:limit]],
        }

    def favorite_folders(self, *, limit: int = 50, page: int = 1) -> dict[str, Any]:
        status = self.status()
        if not status.get("is_login") or not status.get("mid"):
            raise LoginRequiredError("Login is required to list your favorite folders")
        return self.user_favorites(status["mid"], limit=limit, page=page)

    def like_video(self, video_id: str, *, unlike: bool = False) -> dict[str, Any]:
        token = self._require_write_session()
        detail = self.video_detail(video_id)
        payload = self.post_json(
            constants.ARCHIVE_LIKE_URL,
            data={"aid": detail.get("aid"), "like": 2 if unlike else 1, "csrf": token},
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        return {"action": "unlike" if unlike else "like", "video": _video_summary(detail), "data": payload.get("data")}

    def coin_video(self, video_id: str, *, count: int = 1, select_like: bool = False) -> dict[str, Any]:
        token = self._require_write_session()
        detail = self.video_detail(video_id)
        payload = self.post_json(
            constants.COIN_ADD_URL,
            data={
                "aid": detail.get("aid"),
                "multiply": min(max(count, 1), 2),
                "select_like": 1 if select_like else 0,
                "csrf": token,
            },
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        return {"action": "coin", "video": _video_summary(detail), "data": payload.get("data")}

    def favorite_video(self, video_id: str, *, folder_id: str | int, remove: bool = False) -> dict[str, Any]:
        token = self._require_write_session()
        detail = self.video_detail(video_id)
        media_key = "del_media_ids" if remove else "add_media_ids"
        payload = self.post_json(
            constants.FAVORITE_DEAL_URL,
            data={
                "rid": detail.get("aid"),
                "type": 2,
                media_key: str(folder_id),
                "csrf": token,
            },
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        return {"action": "favorite.remove" if remove else "favorite.add", "video": _video_summary(detail), "folder_id": str(folder_id), "data": payload.get("data")}

    def watchlater_add(self, video_id: str) -> dict[str, Any]:
        token = self._require_write_session()
        detail = self.video_detail(video_id)
        payload = self.post_json(
            constants.WATCHLATER_ADD_URL,
            data={"aid": detail.get("aid"), "csrf": token},
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        return {"action": "watchlater.add", "video": _video_summary(detail), "data": payload.get("data")}

    def follow_user(self, mid: str | int, *, unfollow: bool = False) -> dict[str, Any]:
        token = self._require_write_session()
        user_mid = _normalize_mid(mid)
        payload = self.post_json(
            constants.RELATION_MODIFY_URL,
            data={"fid": user_mid, "act": 2 if unfollow else 1, "re_src": 11, "csrf": token},
            headers={"Referer": f"https://space.bilibili.com/{user_mid}/"},
        )
        return {"action": "unfollow" if unfollow else "follow", "mid": str(user_mid), "data": payload.get("data")}

    def comment_post(
        self,
        video_id: str,
        message: str,
        *,
        root: str | int | None = None,
        parent: str | int | None = None,
    ) -> dict[str, Any]:
        token = self._require_write_session()
        detail = self.video_detail(video_id)
        data: dict[str, Any] = {"type": 1, "oid": detail.get("aid"), "message": message, "csrf": token}
        if root:
            data["root"] = root
        if parent:
            data["parent"] = parent
        payload = self.post_json(
            constants.COMMENT_ADD_URL,
            data=data,
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        return {"action": "comment.post", "video": _video_summary(detail), "reply": _normalize_comment(payload.get("data") or {})}

    def comment_delete(self, video_id: str, *, rpid: str | int) -> dict[str, Any]:
        token = self._require_write_session()
        detail = self.video_detail(video_id)
        payload = self.post_json(
            constants.COMMENT_DELETE_URL,
            data={"type": 1, "oid": detail.get("aid"), "rpid": rpid, "csrf": token},
            headers={"Referer": video_url(detail.get("bvid"), detail.get("aid"))},
        )
        return {"action": "comment.delete", "video": _video_summary(detail), "rpid": str(rpid), "data": payload.get("data")}

    def _relation_list(self, mid: str | int, *, relation: str, limit: int, page: int) -> dict[str, Any]:
        user_mid = _normalize_mid(mid)
        url = constants.RELATION_FOLLOWINGS_URL if relation == "following" else constants.RELATION_FOLLOWERS_URL
        params = {
            "vmid": user_mid,
            "pn": max(page, 1),
            "ps": min(max(limit, 1), 50),
            "order_type": "attention",
        }
        payload = self.get_json(
            url,
            params=params,
            headers={"Referer": f"https://space.bilibili.com/{user_mid}/relation/{'follow' if relation == 'following' else 'fans'}"},
        )
        data = payload.get("data") or {}
        raw_items = data.get("list") or []
        return {
            "mid": str(user_mid),
            "relation": relation,
            "page": max(page, 1),
            "limit": limit,
            "total": data.get("total"),
            "items": [_normalize_relation_user(item) for item in raw_items[:limit]],
        }

    def _optional_data(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            payload = self.get_json(url, params=params, headers=headers)
        except BiliError:
            return {}
        data = payload.get("data") or {}
        return data if isinstance(data, dict) else {}

    def _require_write_session(self) -> str:
        token = csrf_token(self.account)
        if not token:
            raise LoginRequiredError()
        status = self.status()
        if not status.get("is_login"):
            raise LoginRequiredError()
        return token


def _video_params(ref: VideoRef) -> dict[str, Any]:
    if ref.bvid:
        return {"bvid": ref.bvid}
    if ref.aid is not None:
        return {"aid": ref.aid}
    return {"bvid": ref.raw}


def _normalize_mid(value: str | int) -> int:
    text = str(value).strip()
    if not text.isdigit():
        raise APIError(f"Unsupported user mid: {value}", "UNSUPPORTED_INPUT")
    return int(text)


def _quality_to_qn(value: str | int) -> int:
    if isinstance(value, int):
        return value
    text = str(value).lower()
    if text.isdigit():
        return int(text)
    return constants.QUALITY_MAP.get(text, 127)


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


def _normalize_user_info(
    data: dict[str, Any],
    *,
    relation: dict[str, Any],
    navnum: dict[str, Any],
    setting: dict[str, Any],
    mid: int,
) -> dict[str, Any]:
    card = data.get("card") or {}
    official_verify = card.get("official_verify") or {}
    official_detail = card.get("Official") or {}
    level = card.get("level_info") or {}
    vip = card.get("vip") or {}
    return {
        "mid": str(card.get("mid") or mid),
        "name": card.get("name") or "",
        "sex": card.get("sex") or "",
        "face": card.get("face") or "",
        "sign": card.get("sign") or "",
        "url": f"https://space.bilibili.com/{card.get('mid') or mid}",
        "level": level.get("current_level"),
        "vip": {
            "type": vip.get("type"),
            "status": vip.get("status"),
            "label": (vip.get("label") or {}).get("text"),
        },
        "official": {
            "type": official_verify.get("type", official_detail.get("type")),
            "role": official_detail.get("role"),
            "title": official_detail.get("title") or official_verify.get("desc") or "",
            "desc": official_verify.get("desc") or official_detail.get("desc") or "",
        },
        "counts": {
            "following": relation.get("following") or card.get("attention") or card.get("friend"),
            "followers": relation.get("follower") or data.get("follower") or card.get("fans"),
            "archive": data.get("archive_count"),
            "article": data.get("article_count"),
            "likes": data.get("like_num"),
            "video": navnum.get("video"),
            "favorite_master": (navnum.get("favourite") or {}).get("master"),
            "favorite_guest": (navnum.get("favourite") or {}).get("guest"),
            "bangumi": navnum.get("bangumi"),
            "cinema": navnum.get("cinema"),
            "album": navnum.get("album"),
            "audio": navnum.get("audio"),
            "opus": navnum.get("opus"),
        },
        "privacy": setting.get("privacy") or {},
    }


def _normalize_space_video(item: dict[str, Any]) -> dict[str, Any]:
    bvid = item.get("bvid")
    aid = item.get("aid")
    return {
        "type": "video",
        "bvid": bvid,
        "aid": aid,
        "title": _clean(item.get("title")),
        "author": _clean(item.get("author")),
        "mid": item.get("mid"),
        "play": item.get("play"),
        "comment": item.get("comment"),
        "danmaku": item.get("video_review"),
        "duration": item.get("length"),
        "created": item.get("created"),
        "description": _clean(item.get("description")),
        "pic": item.get("pic"),
        "url": item.get("arcurl") or video_url(bvid, aid),
    }


def _normalize_relation_user(item: dict[str, Any]) -> dict[str, Any]:
    mid = item.get("mid")
    official = item.get("official_verify") or {}
    vip = item.get("vip") or {}
    return {
        "type": "user",
        "mid": str(mid) if mid is not None else "",
        "name": item.get("uname") or item.get("name") or "",
        "uname": item.get("uname") or item.get("name") or "",
        "face": item.get("face") or "",
        "sign": item.get("sign") or "",
        "level": item.get("level"),
        "mtime": item.get("mtime"),
        "official": {
            "type": official.get("type"),
            "desc": official.get("desc") or "",
        },
        "vip": {
            "type": vip.get("vipType") or vip.get("type"),
            "status": vip.get("vipStatus") or vip.get("status"),
        },
        "url": f"https://space.bilibili.com/{mid}" if mid else "",
    }


def _normalize_favorite_folder(item: dict[str, Any]) -> dict[str, Any]:
    folder_id = item.get("id") or item.get("fid")
    return {
        "type": "favorite_folder",
        "id": folder_id,
        "fid": folder_id,
        "mid": item.get("mid"),
        "title": item.get("title") or "",
        "media_count": item.get("media_count"),
        "fav_state": item.get("fav_state"),
        "attr": item.get("attr"),
        "cover": item.get("cover") or "",
        "url": f"https://space.bilibili.com/{item.get('mid')}/favlist?fid={folder_id}" if item.get("mid") and folder_id else "",
    }


def _live_play_params(room_id: str | int) -> dict[str, Any]:
    return {
        "room_id": room_id,
        "protocol": "0,1",
        "format": "0,1,2",
        "codec": "0,1",
        "qn": 10000,
        "platform": "web",
        "ptype": 8,
    }


def _normalize_live_search_item(item: dict[str, Any]) -> dict[str, Any]:
    room_id = item.get("room_id") or item.get("id")
    return {
        "type": "live",
        "room_id": room_id,
        "id": room_id,
        "uid": item.get("mid") or item.get("uid"),
        "title": _clean(item.get("title")),
        "anchor": _clean(item.get("author") or item.get("uname")),
        "online": item.get("online"),
        "cover": item.get("cover"),
        "url": f"https://live.bilibili.com/{room_id}" if room_id else "",
    }


def _normalize_live_room_card(item: dict[str, Any]) -> dict[str, Any]:
    room_id = item.get("roomid") or item.get("room_id")
    return {
        "type": "live",
        "room_id": room_id,
        "id": room_id,
        "uid": item.get("uid"),
        "title": _clean(item.get("title")),
        "anchor": _clean(item.get("uname")),
        "online": item.get("online"),
        "cover": item.get("cover"),
        "keyframe": item.get("keyframe"),
        "area": {
            "id": item.get("area_v2_id"),
            "name": item.get("area_v2_name"),
            "parent_id": item.get("area_v2_parent_id"),
            "parent_name": item.get("area_v2_parent_name"),
        },
        "url": f"https://live.bilibili.com/{room_id}" if room_id else "",
    }


def _normalize_live_info(room: dict[str, Any], *, anchor: dict[str, Any], play: dict[str, Any], show_urls: bool) -> dict[str, Any]:
    anchor_info = anchor.get("info") or {}
    room_id = room.get("room_id")
    return {
        "type": "live",
        "room_id": str(room_id or ""),
        "short_id": room.get("short_id"),
        "uid": room.get("uid"),
        "title": _clean(room.get("title")),
        "description": _clean(room.get("description")),
        "live_status": room.get("live_status"),
        "status": _live_status_name(room.get("live_status")),
        "is_live": room.get("live_status") == 1,
        "online": room.get("online"),
        "attention": room.get("attention"),
        "live_time": room.get("live_time"),
        "cover": room.get("user_cover") or room.get("keyframe") or room.get("background"),
        "keyframe": room.get("keyframe"),
        "background": room.get("background"),
        "tags": [tag.strip() for tag in str(room.get("tags") or "").split(",") if tag.strip()],
        "area": {
            "id": room.get("area_id"),
            "name": room.get("area_name"),
            "parent_id": room.get("parent_area_id"),
            "parent_name": room.get("parent_area_name"),
        },
        "anchor": {
            "uid": anchor_info.get("uid") or room.get("uid"),
            "name": anchor_info.get("uname") or "",
            "face": anchor_info.get("face") or "",
            "level": anchor_info.get("platform_user_level"),
            "official": anchor_info.get("official_verify") or {},
        },
        "streams": _extract_live_streams(play, show_urls=show_urls),
        "qualities": _live_quality_desc(play),
        "url": f"https://live.bilibili.com/{room_id}" if room_id else "",
    }


def _extract_live_streams(play: dict[str, Any], *, show_urls: bool) -> list[dict[str, Any]]:
    playurl = (play.get("playurl_info") or {}).get("playurl") or {}
    streams = []
    for stream in playurl.get("stream") or []:
        protocol = stream.get("protocol_name") or ""
        for fmt in stream.get("format") or []:
            format_name = fmt.get("format_name") or ""
            for codec in fmt.get("codec") or []:
                urls = _live_stream_urls(codec)
                public = {
                    "protocol": protocol,
                    "format": format_name,
                    "codec": codec.get("codec_name") or "",
                    "current_qn": codec.get("current_qn"),
                    "accept_qn": codec.get("accept_qn") or [],
                    "url_present": bool(urls),
                    "url_count": len(urls),
                }
                if show_urls:
                    public["urls"] = urls
                    public["url"] = urls[0] if urls else ""
                streams.append(public)
    return streams


def _live_stream_urls(codec: dict[str, Any]) -> list[str]:
    base_url = codec.get("base_url") or codec.get("baseUrl") or ""
    if not base_url:
        return []
    urls = []
    for item in codec.get("url_info") or []:
        host = item.get("host") or ""
        extra = item.get("extra") or ""
        if base_url.startswith("http"):
            url = base_url
        else:
            url = host.rstrip("/") + base_url
        if extra:
            if url.endswith("?") or extra.startswith("?"):
                url += extra
            else:
                url += "?" + extra
        urls.append(url)
    return urls


def _live_quality_desc(play: dict[str, Any]) -> list[dict[str, Any]]:
    playurl = (play.get("playurl_info") or {}).get("playurl") or {}
    return [{"qn": item.get("qn"), "desc": item.get("desc")} for item in playurl.get("g_qn_desc") or []]


def _live_status_name(value: Any) -> str:
    if value == 1:
        return "live"
    if value == 2:
        return "round"
    return "offline"


def _normalize_live_danmaku(item: dict[str, Any]) -> dict[str, Any]:
    user_level = item.get("user_level") or []
    medal = item.get("medal") or []
    return {
        "id": item.get("id_str") or item.get("id") or item.get("rnd"),
        "text": item.get("text") or "",
        "uid": item.get("uid"),
        "uname": item.get("nickname") or item.get("uname") or "",
        "timeline": item.get("timeline") or "",
        "is_admin": bool(item.get("isadmin")),
        "vip": item.get("vip"),
        "svip": item.get("svip"),
        "guard_level": item.get("guard_level"),
        "user_level": user_level[0] if user_level else None,
        "medal": {
            "name": medal[1] if len(medal) > 1 else "",
            "level": medal[0] if medal else None,
        },
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
