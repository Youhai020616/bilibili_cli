"""Error types and structured error helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BiliError(Exception):
    code: str
    message: str
    retryable: bool = False
    next_action: str | None = None

    def __str__(self) -> str:
        return self.message


class LoginRequiredError(BiliError):
    def __init__(self, message: str = "Login is required for this operation"):
        super().__init__("LOGIN_REQUIRED", message, True, "Run `bili login` and retry")


class SessionExpiredError(BiliError):
    def __init__(self, message: str = "Saved session is expired"):
        super().__init__("SESSION_EXPIRED", message, True, "Run `bili login` again")


class CaptchaRequiredError(BiliError):
    def __init__(self, message: str = "Bilibili returned a risk or captcha response"):
        super().__init__("CAPTCHA_REQUIRED", message, True, "Open a browser session or retry later")


class RateLimitedError(BiliError):
    def __init__(self, message: str = "Request was rate limited"):
        super().__init__("RATE_LIMITED", message, True, "Wait and retry with a lower rate")


class NotFoundError(BiliError):
    def __init__(self, message: str = "Requested resource was not found"):
        super().__init__("VIDEO_NOT_FOUND", message, False, None)


class APIError(BiliError):
    def __init__(self, message: str, code: str = "API_ERROR", retryable: bool = False, next_action: str | None = None):
        super().__init__(code, message, retryable, next_action)


class UnsupportedInputError(BiliError):
    def __init__(self, message: str):
        super().__init__("UNSUPPORTED_INPUT", message, False, None)


def map_api_code(code: int, message: str) -> BiliError:
    if code == -101:
        return LoginRequiredError(message or "Not logged in")
    if code in {-352, -412}:
        return CaptchaRequiredError(message or "Risk verification required")
    if code in {-404, 62002}:
        return NotFoundError(message or "Resource not found")
    if code in {-509, 429}:
        return RateLimitedError(message or "Rate limited")
    return APIError(message or f"Bilibili API returned code {code}", "API_ERROR")
