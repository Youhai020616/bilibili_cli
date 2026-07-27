"""Sanitization helpers for logs and filenames."""

from __future__ import annotations

import re

SENSITIVE_KEYS = ("SESSDATA", "bili_jct", "DedeUserID", "sid")


def sanitize_cookie_header(value: str) -> str:
    sanitized = value
    for key in SENSITIVE_KEYS:
        sanitized = re.sub(rf"{re.escape(key)}=[^;]+", f"{key}=<redacted>", sanitized)
    return sanitized


def safe_filename(value: str, max_length: int = 120) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip()
    text = re.sub(r"\s+", " ", text)
    return (text[:max_length] or "untitled").rstrip(". ")
