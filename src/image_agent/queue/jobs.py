"""In-memory BullMQ-compatible job facade for local development/tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class JobRecord:
    id: str
    kind: str
    payload: dict
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InMemoryJobQueue:
    def __init__(self) -> None:
        self.jobs: dict[str, JobRecord] = {}

    def enqueue(self, kind: str, payload: dict, prefix: str = "job") -> JobRecord:
        job = JobRecord(id=f"{prefix}_{uuid4().hex[:12]}", kind=kind, payload=payload)
        self.jobs[job.id] = job
        return job

    def health(self) -> dict[str, str | int]:
        return {"status": "ok", "backend": "in-memory", "queued_jobs": sum(1 for j in self.jobs.values() if j.status == "queued")}
