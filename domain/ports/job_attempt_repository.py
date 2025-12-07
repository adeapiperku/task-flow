from __future__ import annotations

from typing import Protocol, List
from uuid import UUID

from domain.models.job_attempt import JobAttempt

class JobAttemptRepository(Protocol):
    """
    Port for persisting and loading job attempts.

    The domain layer depends on this protocol, not on any concrete DB code.
    """

    async def insert(self, job_attempt: JobAttempt) -> JobAttempt:
        """
        Persist a new JobAttempt.

        Contract:
        - Must fail if a job attempt with the same id already exists.
        - Returns the stored JobAttempt (may be identical for now).
        """
        ...

    async def list_for_job(self, job_id: UUID) -> List[JobAttempt]:
        """
        Retrieve all JobAttempts for a given Job ID.

        Returns a list of JobAttempts if found, or an empty list if none exist.
        """
        ...