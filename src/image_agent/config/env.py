"""Environment-backed configuration for the image processing API."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    api_keys: tuple[str, ...] = ("dev-key",)
    max_upload_bytes: int = 100 * 1024 * 1024
    max_resize_width: int = 2000
    min_dimension: int = 10
    max_dimension: int = 8000
    storage_root: str = "./data/images"
    public_base_url: str = ""
    imgproxy_url: str = "http://imgproxy:8080"
    imgproxy_signature_key: str = "your-secret-key"
    imgproxy_signature_salt: str = "your-secret-salt"
    redis_url: str = "redis://redis:6379"
    minio_endpoint: str = "minio:9000"
    storage_gb_month_usd: float = 0.023
    cpu_second_usd: float = 0.000011
    bandwidth_gb_usd: float = 0.09


def load_settings() -> Settings:
    keys = tuple(k.strip() for k in os.getenv("IMAGE_AGENT_API_KEYS", "dev-key").split(",") if k.strip())
    return Settings(
        api_keys=keys or ("dev-key",),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024))),
        max_resize_width=int(os.getenv("MAX_RESIZE_WIDTH", "2000")),
        storage_root=os.getenv("STORAGE_ROOT", "./data/images"),
        public_base_url=os.getenv("PUBLIC_BASE_URL", ""),
        imgproxy_url=os.getenv("IMGPROXY_URL", "http://imgproxy:8080"),
        imgproxy_signature_key=os.getenv("IMGPROXY_SIGNATURE_KEY", "your-secret-key"),
        imgproxy_signature_salt=os.getenv("IMGPROXY_SIGNATURE_SALT", "your-secret-salt"),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379"),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
        storage_gb_month_usd=float(os.getenv("STORAGE_GB_MONTH_USD", "0.023")),
        cpu_second_usd=float(os.getenv("CPU_SECOND_USD", "0.000011")),
        bandwidth_gb_usd=float(os.getenv("BANDWIDTH_GB_USD", "0.09")),
    )
