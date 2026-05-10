"""Structured JSON logging helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("image_agent")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_event(event: str, **fields: Any) -> None:
    logger.info(json.dumps({"event": event, **fields}, sort_keys=True))
