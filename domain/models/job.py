from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from domain.models.retry_policy import RetryPolicy, RetryStrategy


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

    retry_policy: RetryPolicy


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
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        retry_base_delay_seconds: int = 30,
    ) -> "Job":
        """
        Factory for creating a new job with sane defaults.
        """
        now = datetime.utcnow()
        policy = RetryPolicy(
            strategy=retry_strategy,
            base_delay_seconds=retry_base_delay_seconds,
        )
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
            next_run_at=scheduled_at,
            last_run_at=None,
            attempts=0,
            max_attempts=max_attempts,
            archived=False,
            locked_by=None,
            locked_at=None,
            retry_policy=policy,
        )

    def mark_scheduled(self, when: datetime) -> "Job":
        return self._replace(
            state=JobState.SCHEDULED,
            next_run_at=when,
        )

    def mark_succeeded(self, *, now: Optional[datetime] = None) -> "Job":
        now = now or datetime.utcnow()
        return self._replace(
            state=JobState.SUCCEEDED,
            last_run_at=now,
            next_run_at=None,
            locked_by=None,
            locked_at=None,
        )

    def apply_failure(
        self,
        *,
        now: Optional[datetime] = None,
    ) -> "Job":
        """
        Apply a failure according to this job's retry policy.

        - increments attempts
        - either schedules a retry (state=SCHEDULED, next_run_at in future)
        - or marks job DEAD when attempts exhausted
        """
        now = now or datetime.utcnow()
        attempts = self.attempts + 1

        next_run_at = self.retry_policy.compute_next_run_at(
            attempts_after_increment=attempts,
            max_attempts=self.max_attempts,
            now=now,
        )

        if next_run_at is None:
            return self._replace(
                attempts=attempts,
                state=JobState.DEAD,
                last_run_at=now,
                next_run_at=None,
                locked_by=None,
                locked_at=None,
            )

        return self._replace(
            attempts=attempts,
            state=JobState.SCHEDULED,
            last_run_at=now,
            next_run_at=next_run_at,
            locked_by=None,
            locked_at=None,
        )

    def _replace(self, **changes: Any) -> "Job":
        data = {**self.__dict__, **changes}
        if "updated_at" not in changes:
            data["updated_at"] = datetime.utcnow()
        return Job(**data)
