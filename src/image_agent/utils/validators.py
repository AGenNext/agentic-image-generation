"""Input validation and SSRF protection helpers."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_FORMATS = {"jpeg", "jpg", "png", "webp", "avif", "original"}
ALLOWED_MIME_PREFIXES = ("image/",)
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def normalize_formats(values: list[str] | None) -> list[str]:
    formats = values or ["webp", "avif", "original"]
    normalized = []
    for value in formats:
        fmt = value.lower().strip()
        if fmt not in ALLOWED_FORMATS:
            raise ValueError(f"unsupported format: {value}")
        normalized.append("jpeg" if fmt == "jpg" else fmt)
    return list(dict.fromkeys(normalized))


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https", "s3", "data"}:
        raise ValueError("unsupported URL scheme")
    if parsed.scheme in {"s3", "data"}:
        return
    if not parsed.hostname:
        raise ValueError("URL hostname is required")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    for *_, sockaddr in addresses:
        ip = ipaddress.ip_address(sockaddr[0])
        if any(ip in network for network in PRIVATE_NETWORKS):
            raise ValueError("private network URLs are not allowed")
