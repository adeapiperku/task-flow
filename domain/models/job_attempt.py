# domain/models/job_attempt.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class JobAttempt:
    """
    Represents a single execution attempt of a job.
    """

    id: UUID
    job_id: UUID
    attempt_number: int
    started_at: datetime
    finished_at: datetime
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    worker_id: Optional[str]

    @staticmethod
    def new(
        *,
        job_id: UUID,
        attempt_number: int,
        started_at: datetime,
        finished_at: datetime,
        success: bool,
        worker_id: Optional[str],
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> "JobAttempt":
        return JobAttempt(
            id=uuid4(),
            job_id=job_id,
            attempt_number=attempt_number,
            started_at=started_at,
            finished_at=finished_at,
            success=success,
            error_type=error_type,
            error_message=error_message,
            worker_id=worker_id,
        )
