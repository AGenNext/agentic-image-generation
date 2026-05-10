"""Metadata and lightweight image analysis processor."""

from __future__ import annotations

from collections import Counter
from io import BytesIO
import time

from PIL import Image, ExifTags


class MetadataProcessor:
    def analyze(self, data: bytes, requested: list[str]) -> dict:
        started = time.perf_counter()
        response: dict = {"processing_time_ms": 0}
        with Image.open(BytesIO(data)) as image:
            image.load()
            if "exif" in requested:
                raw = image.getexif()
                tags = {ExifTags.TAGS.get(k, str(k)): str(v) for k, v in raw.items()}
                response["exif"] = {"width": image.width, "height": image.height, "format": image.format, "camera": tags.get("Model", ""), "created_at": tags.get("DateTimeOriginal", "")}
            if "colors" in requested:
                thumb = image.convert("RGB").resize((64, 64))
                counts = Counter(thumb.getdata()).most_common(5)
                total = 64 * 64
                response["colors"] = [{"hex": "#%02X%02X%02X" % color, "percentage": round(count / total * 100, 2)} for color, count in counts]
            if "objects" in requested:
                response["objects"] = []
            if "text" in requested:
                response["text"] = []
        response["processing_time_ms"] = int((time.perf_counter() - started) * 1000)
        return response
