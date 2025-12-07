# domain/ports/job_repository.py
from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.models.job import Job


class JobRepository(Protocol):
    """
    Port for persisting and loading jobs.

    The domain layer depends on this protocol, not on any concrete DB code.
    """

    async def insert(self, job: Job) -> Job:
        """
        Persist a new Job.

        Contract:
        - Must fail if a job with the same id already exists.
        - Returns the stored Job (may be identical for now).
        """
        ...

    async def get_by_id(self, job_id: UUID) -> Job | None:
        """
        Retrieve a Job by its ID.

        Returns the Job if found, or None if not found.
        """
        ...

    async def update(self, job: Job) -> Job:
        """
        Update an existing Job.

        Contract:
        - Must fail if the job does not exist.
        - Returns the updated Job (may be identical for now).
        """
        ...

    async def acquire_next_due_job(
            self,
            *,
            queue: str,
            now: datetime,
            worker_id: str,
    ) -> Job | None:
        """
        Atomically select and lock the next runnable job for a worker.

        Selection rules (v0):
        - state in (PENDING, SCHEDULED)
        - archived = false
        - (next_run_at IS NULL OR next_run_at <= now)
        - queue matches
        - ordered by priority DESC, created_at ASC

        Side effects:
        - Sets locked_by, locked_at
        - Sets state to RUNNING

        Returns:
        - Job if one was acquired
        - None if no job is available
        """
        ...