from __future__ import annotations

from datetime import datetime
import logging
from typing import Callable

from application.uow import UnitOfWork
from domain.models.job import Job

logger = logging.getLogger(__name__)

class AcquireNextJobUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(
        self,
        *,
        queue: str,
        worker_id: str,
        visibility_timeout_s: int = 300,
    ) -> Job | None:
        now = datetime.utcnow()
        async with self._uow_factory() as uow:
            logger.debug(
                "acquire_next_job: queue=%s worker_id=%s visibility_timeout_s=%s",
                queue,
                worker_id,
                visibility_timeout_s,
            )
            job = await uow.job_repo.acquire_next_due_job(
                queue=queue,
                now=now,
                worker_id=worker_id,
                visibility_timeout_s=visibility_timeout_s,
            )
            if job:
                logger.info(
                    "acquire_next_job: acquired job_id=%s name=%s state=%s",
                    job.id,
                    job.name,
                    job.state.value,
                )
            else:
                logger.debug("acquire_next_job: no job available")
            return job
