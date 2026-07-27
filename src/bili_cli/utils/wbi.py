"""Bilibili WBI signing helpers."""

from __future__ import annotations

from hashlib import md5
from time import time
from typing import Any, Mapping
from urllib.parse import urlencode

MIXIN_KEY_ENC_TAB = [
    46,
    47,
    18,
    2,
    53,
    8,
    23,
    32,
    15,
    50,
    10,
    31,
    58,
    3,
    45,
    35,
    27,
    43,
    5,
    49,
    33,
    9,
    42,
    19,
    29,
    28,
    14,
    39,
    12,
    38,
    41,
    13,
    37,
    48,
    7,
    16,
    24,
    55,
    40,
    61,
    26,
    17,
    0,
    1,
    60,
    51,
    30,
    4,
    22,
    25,
    54,
    21,
    56,
    59,
    6,
    63,
    57,
    62,
    11,
    36,
    20,
    34,
    44,
    52,
]


def extract_wbi_keys(nav_data: Mapping[str, Any]) -> tuple[str, str]:
    wbi_img = nav_data.get("wbi_img") or {}
    img_url = str(wbi_img.get("img_url") or "")
    sub_url = str(wbi_img.get("sub_url") or "")
    if not img_url or not sub_url:
        raise ValueError("Missing WBI keys in nav payload")
    img_key = img_url.rsplit("/", 1)[-1].split(".", 1)[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".", 1)[0]
    return img_key, sub_key


def mixin_key(img_key: str, sub_key: str) -> str:
    source = img_key + sub_key
    return "".join(source[index] for index in MIXIN_KEY_ENC_TAB)[:32]


def wbi_sign(
    params: Mapping[str, Any],
    *,
    img_key: str,
    sub_key: str,
    timestamp: int | None = None,
) -> dict[str, Any]:
    signed = {key: value for key, value in params.items() if value is not None}
    signed["wts"] = int(time()) if timestamp is None else int(timestamp)
    ordered = dict(sorted(signed.items()))
    cleaned = {key: "".join(ch for ch in str(value) if ch not in "!'()*") for key, value in ordered.items()}
    query = urlencode(cleaned)
    cleaned["w_rid"] = md5((query + mixin_key(img_key, sub_key)).encode()).hexdigest()
    return cleaned
