"""Pillow/libjpeg processor with a sharp-compatible role in the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import time

from PIL import Image


@dataclass(frozen=True)
class ProcessedVariant:
    format: str
    bytes: bytes
    width: int
    height: int
    processing_time_ms: int


class ImageProcessor:
    def process(self, data: bytes, *, formats: list[str], quality: int = 80, resize_width: int | None = None) -> list[ProcessedVariant]:
        started = time.perf_counter()
        with Image.open(BytesIO(data)) as image:
            image.load()
            if image.width < 10 or image.height < 10 or image.width > 8000 or image.height > 8000:
                raise ValueError("image dimensions must be between 10x10 and 8000x8000")
            if resize_width:
                ratio = resize_width / image.width
                target = (resize_width, max(1, round(image.height * ratio)))
                image = image.resize(target, Image.Resampling.LANCZOS)
            variants: list[ProcessedVariant] = []
            for fmt in formats:
                variant_started = time.perf_counter()
                if fmt == "original":
                    variants.append(ProcessedVariant("original", data, image.width, image.height, int((time.perf_counter() - started) * 1000)))
                    continue
                output = BytesIO()
                target = image.convert("RGB") if fmt in {"jpeg", "webp", "avif"} else image
                save_format = "JPEG" if fmt == "jpeg" else fmt.upper()
                try:
                    target.save(output, format=save_format, quality=quality, optimize=True)
                except Exception:
                    if fmt == "avif":
                        fallback = BytesIO()
                        target.save(fallback, format="WEBP", quality=quality, optimize=True)
                        variants.append(ProcessedVariant("webp", fallback.getvalue(), image.width, image.height, int((time.perf_counter() - variant_started) * 1000)))
                        continue
                    raise
                variants.append(ProcessedVariant(fmt, output.getvalue(), image.width, image.height, int((time.perf_counter() - variant_started) * 1000)))
            return variants
