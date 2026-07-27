"""Shared constants for Bilibili web/API access."""

BILI_DOMAIN = "https://www.bilibili.com"
API_DOMAIN = "https://api.bilibili.com"
LIVE_API_DOMAIN = "https://api.live.bilibili.com"

NAV_URL = f"{API_DOMAIN}/x/web-interface/nav"
SEARCH_URL = f"{API_DOMAIN}/x/web-interface/search/type"
VIDEO_VIEW_URL = f"{API_DOMAIN}/x/web-interface/view"
VIDEO_TAGS_URL = f"{API_DOMAIN}/x/tag/archive/tags"
VIDEO_RELATED_URL = f"{API_DOMAIN}/x/web-interface/archive/related"
COMMENTS_MAIN_URL = f"{API_DOMAIN}/x/v2/reply/main"
COMMENTS_REPLY_URL = f"{API_DOMAIN}/x/v2/reply/reply"
POPULAR_URL = f"{API_DOMAIN}/x/web-interface/popular"
RANKING_URL = f"{API_DOMAIN}/x/web-interface/ranking/v2"
HOT_SEARCH_URL = f"{API_DOMAIN}/x/web-interface/wbi/search/square"
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
FAVORITE_RESOURCE_LIST_URL = f"{API_DOMAIN}/x/v3/fav/resource/list"
ARCHIVE_LIKE_URL = f"{API_DOMAIN}/x/web-interface/archive/like"
COIN_ADD_URL = f"{API_DOMAIN}/x/web-interface/coin/add"
FAVORITE_DEAL_URL = f"{API_DOMAIN}/x/v3/fav/resource/deal"
WATCHLATER_ADD_URL = f"{API_DOMAIN}/x/v2/history/toview/add"
RELATION_MODIFY_URL = f"{API_DOMAIN}/x/relation/modify"
COMMENT_ADD_URL = f"{API_DOMAIN}/x/v2/reply/add"
COMMENT_DELETE_URL = f"{API_DOMAIN}/x/v2/reply/del"
LIVE_MAIN_LIST_URL = f"{LIVE_API_DOMAIN}/xlive/web-interface/v1/webMain/getList"
LIVE_ROOM_INFO_URL = f"{LIVE_API_DOMAIN}/room/v1/Room/get_info"
LIVE_ANCHOR_INFO_URL = f"{LIVE_API_DOMAIN}/live_user/v1/UserInfo/get_anchor_in_room"
LIVE_PLAY_INFO_URL = f"{LIVE_API_DOMAIN}/xlive/web-room/v2/index/getRoomPlayInfo"
LIVE_DANMU_CONF_URL = f"{LIVE_API_DOMAIN}/room/v1/Danmu/getConf"
LIVE_DANMAKU_HISTORY_URL = f"{LIVE_API_DOMAIN}/xlive/web-room/v1/dM/gethistory"
CREATOR_HOME_URL = "https://member.bilibili.com/platform/home"
CREATOR_UPLOAD_URL = "https://member.bilibili.com/platform/upload/video/frame"
CREATOR_VIDEO_MANAGER_URL = "https://member.bilibili.com/platform/upload-manager/article"
MSGFEED_UNREAD_URL = f"{API_DOMAIN}/x/msgfeed/unread"
VC_SESSION_LIST_URL = "https://api.vc.bilibili.com/session_svr/v1/session_svr/get_sessions"

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
