from __future__ import annotations

from typing import Callable

from application.uow import UnitOfWork
from domain.models.job import Job


class GetJobByIdUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, job_id) -> Job:
        async with self._uow_factory() as uow:
            job = await uow.job_repo.get_by_id(job_id)
            return job