from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from application.uow import UnitOfWork
from domain.exceptions import NotFoundError
from domain.models.job import Job

class FailJobUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, job_id: UUID) -> Job:
        now = datetime.utcnow()
        async with self._uow_factory() as uow:
            job = await uow.job_repo.get_by_id(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} not found")

            # dead if we've reached or exceeded max attempts
            will_be_dead = job.attempts + 1 >= job.max_attempts
            updated = job.mark_failed(now, dead=will_be_dead)
            stored = await uow.job_repo.update(updated)
            return stored