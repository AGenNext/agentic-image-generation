"""Local filesystem implementation of the storage abstraction.

The interface is intentionally S3-shaped so the same API can be backed by
MinIO/S3 in production while tests and local development remain dependency-free.
"""

from __future__ import annotations

from pathlib import Path


class LocalImageStorage:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes) -> str:
        safe = key.lstrip("/")
        path = self.root / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return safe

    def get_bytes(self, key: str) -> bytes:
        return (self.root / key.lstrip("/")).read_bytes()

    def exists(self, key: str) -> bool:
        return (self.root / key.lstrip("/")).exists()

    def health(self) -> dict[str, str]:
        probe = self.root / ".health"
        probe.write_text("ok")
        return {"status": "ok", "backend": "local", "root": str(self.root)}
