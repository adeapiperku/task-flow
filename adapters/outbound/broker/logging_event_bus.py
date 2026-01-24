from __future__ import annotations

import logging
from typing import Optional

from domain.models.job import Job
from domain.ports.event_bus import EventBus

logger = logging.getLogger(__name__)


class LoggingEventBus(EventBus):
    """
    Simple event bus adapter that logs events.

    Useful for local development and as a default no-op implementation.
    """

    async def publish_job_created(self, job: Job) -> None:
        logger.info("event=job_created job_id=%s name=%s", job.id, job.name)

    async def publish_job_started(self, job: Job, worker_id: str) -> None:
        logger.info(
            "event=job_started job_id=%s worker_id=%s", job.id, worker_id
        )

    async def publish_job_completed(
        self, job: Job, execution_time_ms: Optional[int] = None
    ) -> None:
        logger.info(
            "event=job_completed job_id=%s execution_time_ms=%s",
            job.id,
            execution_time_ms,
        )

    async def publish_job_failed(
        self, job: Job, error_message: Optional[str] = None
    ) -> None:
        logger.warning(
            "event=job_failed job_id=%s error=%s", job.id, error_message
        )

    async def publish_job_dead(
        self, job: Job, error_message: Optional[str] = None
    ) -> None:
        logger.error(
            "event=job_dead job_id=%s error=%s", job.id, error_message
        )

    async def publish_job_retry_scheduled(self, job: Job, next_run_at: str) -> None:
        logger.info(
            "event=job_retry_scheduled job_id=%s next_run_at=%s",
            job.id,
            next_run_at,
        )
