# domain/models/job.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class JobState(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DEAD = "DEAD"


@dataclass(frozen=True)
class Job:
    """
    Domain representation of a job.

    This is intentionally independent of the DB layer.
    It models the behaviour and invariants of a job,
    not how it is stored.
    """
    id: UUID
    queue: str
    name: str
    payload: Dict[str, Any]
    tenant_id: Optional[str]
    state: JobState
    priority: int
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime]
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    attempts: int
    max_attempts: int
    archived: bool
    locked_by: Optional[str]
    locked_at: Optional[datetime]

    # ---------- factory methods ----------

    @staticmethod
    def new(
        *,
        name: str,
        payload: Dict[str, Any],
        queue: str = "default",
        tenant_id: Optional[str] = None,
        priority: int = 0,
        scheduled_at: Optional[datetime] = None,
        max_attempts: int = 3,
    ) -> "Job":
        """
        Factory for creating a new job with sane defaults.
        This is the only place where a "fresh" Job should be created.
        """
        now = datetime.utcnow()
        return Job(
            id=uuid4(),
            queue=queue,
            name=name,
            payload=payload,
            tenant_id=tenant_id,
            state=JobState.PENDING,
            priority=priority,
            created_at=now,
            updated_at=now,
            scheduled_at=scheduled_at,
            next_run_at=scheduled_at,  # simple v0 behaviour
            last_run_at=None,
            attempts=0,
            max_attempts=max_attempts,
            archived=False,
            locked_by=None,
            locked_at=None,
        )

    def mark_scheduled(self, when: datetime) -> "Job":
        return self._replace(
            state=JobState.SCHEDULED,
            next_run_at=when,
        )

    def _replace(self, **changes: Any) -> "Job":
        """
        Internal helper to preserve immutability (frozen dataclass).
        Returns a new instance with updated fields.
        """
        data = {**self.__dict__, **changes}
        # ensure updated_at always moves forward
        if "updated_at" not in changes:
            data["updated_at"] = datetime.utcnow()
        return Job(**data)

    def __str__(self) -> str:
        return f"Job(id={self.id}, name={self.name}, state={self.state}, queue={self.queue})"

    def __repr__(self) -> str:
        return (
            f"Job(id={self.id!r}, queue={self.queue!r}, name={self.name!r}, "
            f"tenant_id={self.tenant_id!r}, state={self.state!r}, priority={self.priority!r}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r}, "
            f"scheduled_at={self.scheduled_at!r}, next_run_at={self.next_run_at!r}, "
            f"last_run_at={self.last_run_at!r}, attempts={self.attempts!r}, "
            f"max_attempts={self.max_attempts!r}, archived={self.archived!r}, "
            f"locked_by={self.locked_by!r}, locked_at={self.locked_at!r})"
        )

    def mark_running(self, worker_id: str, now: datetime) -> "Job":
        return self._replace(
            state=JobState.RUNNING,
            locked_by=worker_id,
            locked_at=now,
            last_run_at=now,
            attempts=self.attempts + 1,
        )
    def mark_succeeded(self, now: datetime) -> "Job":
        return self._replace(
            state=JobState.SUCCEEDED,
            locked_by=None,
            locked_at=None,
            last_run_at=now,
        )
    def mark_failed(self, now: datetime, *, dead: bool = False) -> "Job":
        return self._replace(
            state=JobState.DEAD if dead else JobState.FAILED,
            locked_by=None,
            locked_at=None,
            last_run_at=now,
        )


