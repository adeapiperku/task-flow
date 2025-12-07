from __future__ import annotations

from typing import Callable

from application.dto.schedule_job_command import ScheduleJobCommand
from application.uow import UnitOfWork
from domain.models.job import Job


class ScheduleJobUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(self, command: ScheduleJobCommand) -> Job:
        job = Job.new(
            name=command.name,
            payload=command.payload,
            queue=command.queue,
            priority=command.priority,
            tenant_id=command.tenant_id,
            max_attempts=command.max_attempts,
            scheduled_at=command.scheduled_at,
        )
        async with self._uow_factory() as uow:
            stored = await uow.job_repo.insert(job)
            return stored

