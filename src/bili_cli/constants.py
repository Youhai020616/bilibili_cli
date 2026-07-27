"""Shared constants for Bilibili web/API access."""

BILI_DOMAIN = "https://www.bilibili.com"
API_DOMAIN = "https://api.bilibili.com"

NAV_URL = f"{API_DOMAIN}/x/web-interface/nav"
SEARCH_URL = f"{API_DOMAIN}/x/web-interface/search/type"
VIDEO_VIEW_URL = f"{API_DOMAIN}/x/web-interface/view"
VIDEO_TAGS_URL = f"{API_DOMAIN}/x/tag/archive/tags"
VIDEO_RELATED_URL = f"{API_DOMAIN}/x/web-interface/archive/related"
COMMENTS_MAIN_URL = f"{API_DOMAIN}/x/v2/reply/main"
COMMENTS_REPLY_URL = f"{API_DOMAIN}/x/v2/reply/reply"
POPULAR_URL = f"{API_DOMAIN}/x/web-interface/popular"
RANKING_URL = f"{API_DOMAIN}/x/web-interface/ranking/v2"
DANMAKU_XML_URL = "https://comment.bilibili.com/{cid}.xml"
PLAYER_PLAYURL_URL = f"{API_DOMAIN}/x/player/playurl"
USER_CARD_URL = f"{API_DOMAIN}/x/web-interface/card"
SPACE_NAVNUM_URL = f"{API_DOMAIN}/x/space/navnum"
SPACE_SETTING_URL = f"{API_DOMAIN}/x/space/setting"
SPACE_ARC_SEARCH_URL = f"{API_DOMAIN}/x/space/arc/search"
RELATION_STAT_URL = f"{API_DOMAIN}/x/relation/stat"
RELATION_FOLLOWERS_URL = f"{API_DOMAIN}/x/relation/followers"
RELATION_FOLLOWINGS_URL = f"{API_DOMAIN}/x/relation/followings"
FAVORITE_CREATED_LIST_URL = f"{API_DOMAIN}/x/v3/fav/folder/created/list"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

SEARCH_TYPE_MAP = {
    "video": "video",
    "user": "bili_user",
    "live": "live",
    "article": "article",
    "bangumi": "media_bangumi",
}

SEARCH_ORDER_MAP = {
    "default": "totalrank",
    "views": "click",
    "new": "pubdate",
    "danmaku": "dm",
    "favorite": "stow",
}

COMMENT_SORT_MODE = {
    "hot": 3,
    "new": 2,
}

QUALITY_MAP = {
    "360p": 16,
    "480p": 32,
    "720p": 64,
    "1080p": 80,
    "1080p+": 112,
    "1080p60": 116,
    "4k": 120,
    "hdr": 125,
    "dolby": 126,
    "8k": 127,
    "best": 127,
}
