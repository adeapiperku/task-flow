# application/use_cases/complete_job.py
from __future__ import annotations

from typing import Callable
from uuid import UUID
from datetime import datetime

from application.uow import UnitOfWork
from domain.exceptions import NotFoundError
from domain.models.job import Job
from domain.models.job_attempt import JobAttempt


class CompleteJobUseCase:
    """
    Mark a job as SUCCEEDED and record an attempt.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(
        self,
        job_id: UUID,
        *,
        started_at: datetime,
        finished_at: datetime,
        worker_id: str,
    ) -> Job:
        async with self._uow_factory() as uow:
            job = await uow.job_repo.get_by_id(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} not found")

            # Attempt number = previous failures + this attempt
            attempt_number = job.attempts + 1

            updated = job.mark_succeeded()
            stored_job = await uow.job_repo.update(updated)

            attempt = JobAttempt.new(
                job_id=job_id,
                attempt_number=attempt_number,
                started_at=started_at,
                finished_at=finished_at,
                success=True,
                worker_id=worker_id,
            )
            await uow.job_attempt_repo.insert(attempt)

            return stored_job
