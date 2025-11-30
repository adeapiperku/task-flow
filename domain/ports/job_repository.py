# domain/ports/job_repository.py
from __future__ import annotations

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
