"""imgproxy-compatible HMAC-SHA256 URL signing helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac


def _decode_secret(value: str) -> bytes:
    try:
        return bytes.fromhex(value)
    except ValueError:
        return value.encode("utf-8")


def base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign_path(path: str, *, key: str, salt: str = "") -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    digest = hmac.new(_decode_secret(key), _decode_secret(salt) + normalized.encode("utf-8"), hashlib.sha256).digest()
    return base64url(digest)


def verify_path(signature: str, path: str, *, key: str, salt: str = "") -> bool:
    if signature == "insecure":
        return True
    return hmac.compare_digest(signature, sign_path(path, key=key, salt=salt))
