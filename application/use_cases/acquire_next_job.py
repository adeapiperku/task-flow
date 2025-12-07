from __future__ import annotations

from datetime import datetime
from typing import Callable

from application.uow import UnitOfWork
from domain.models.job import Job

class AcquireNextJobUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, *, queue: str, worker_id: str) -> Job | None:
        now = datetime.utcnow()
        async with self._uow_factory() as uow:
            job = await uow.job_repo.acquire_next_due_job(
                queue=queue,
                now=now,
                worker_id=worker_id,
            )
            return job