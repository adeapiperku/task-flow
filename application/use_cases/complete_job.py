from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from application.uow import UnitOfWork
from domain.exceptions import NotFoundError
from domain.models.job import Job

class CompleteJobUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, job_id: UUID) -> Job:
        now = datetime.utcnow()
        async with self._uow_factory() as uow:
            job = await uow.job_repo.get_by_id(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} not found")

            updated = job.mark_succeeded(now)
            stored = await uow.job_repo.update(updated)
            return stored