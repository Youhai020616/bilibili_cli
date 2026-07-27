from __future__ import annotations

from bili_cli.utils.wbi import extract_wbi_keys, mixin_key, wbi_sign


def test_extract_wbi_keys() -> None:
    nav = {
        "wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/0123456789abcdef0123456789abcdef01234567.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/89abcdef0123456789abcdef0123456789abcdef.png",
        }
    }
    assert extract_wbi_keys(nav) == (
        "0123456789abcdef0123456789abcdef01234567",
        "89abcdef0123456789abcdef0123456789abcdef",
    )


def test_wbi_sign_adds_required_params() -> None:
    img_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    sub_key = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210"
    signed = wbi_sign({"platform": "web", "limit": 10}, img_key=img_key, sub_key=sub_key, timestamp=1700000000)
    assert signed["platform"] == "web"
    assert signed["limit"] == "10"
    assert signed["wts"] == "1700000000"
    assert len(signed["w_rid"]) == 32
    assert mixin_key(img_key, sub_key)
