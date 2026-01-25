from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from domain.models.job import Job
from worker.core.dispatcher import check_capabilities, dispatch_job

logger = logging.getLogger(__name__)


class JobProcessor:
    """
    Encapsulates job execution flow with heartbeats and state updates.
    """

    def __init__(self, *, config, providers, stats, semaphore, shutdown_event):
        self._config = config
        self._providers = providers
        self._stats = stats
        self._semaphore = semaphore
        self._shutdown_event = shutdown_event

    async def check_capabilities(self, job: Job) -> bool:
        job_def = await self._providers.registry_manager.get_job_definition(job.name)
        if job_def and not check_capabilities(
            required=job_def.capabilities,
            available=self._config.capabilities,
        ):
            logger.warning(
                "Worker %s rejected job %s: missing capabilities. "
                "Required: %s, Available: %s",
                self._config.worker_id,
                job.id,
                job_def.capabilities,
                self._config.capabilities,
            )
            self._stats.jobs_rejected += 1
            await self._fail_job_with_capability_error(job, job_def.capabilities)
            return False
        return True

    async def process(self, job: Job) -> None:
        async with self._semaphore:
            self._stats.jobs_processed += 1

            logger.info(
                "Worker %s processing job %s (%s, attempt %d/%d)",
                self._config.worker_id,
                job.id,
                job.name,
                job.attempts + 1,
                job.max_attempts,
            )

            started_at = datetime.utcnow()
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(job.id)
            )

            try:
                result = await dispatch_job(
                    job=job,
                    plugin_registry=self._providers.plugin_registry,
                    uow_factory=self._providers.uow_factory,
                    prefer_db=self._config.prefer_db,
                )

                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                if result.success:
                    logger.info(
                        "Worker %s job %s succeeded",
                        self._config.worker_id,
                        job.id,
                    )
                    await self._handle_job_success(job, started_at)
                else:
                    logger.info(
                        "Worker %s job %s failed",
                        self._config.worker_id,
                        job.id,
                    )
                    await self._handle_job_failure(job, started_at, result.error)

            except Exception as exc:
                if not heartbeat_task.done():
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass

                await self._handle_job_error(job, started_at, exc)

    async def _heartbeat_loop(self, job_id: str) -> None:
        try:
            while not self._shutdown_event.is_set():
                await asyncio.sleep(self._config.heartbeat_interval_s)
                await self._providers.heartbeat_uc.execute(
                    job_id=job_id,
                    worker_id=self._config.worker_id,
                    visibility_timeout_s=self._config.heartbeat_interval_s,
                )
        except asyncio.CancelledError:
            logger.debug("Heartbeat task for job %s was cancelled", job_id)
            raise
        except Exception as exc:
            logger.error("Error in heartbeat loop for job %s: %s", job_id, exc)

    async def _handle_job_success(self, job: Job, started_at: datetime) -> None:
        finished_at = datetime.utcnow()
        execution_time = (finished_at - started_at).total_seconds()

        logger.info(
            "Job %s completed successfully in %.2fs",
            job.id,
            execution_time,
        )

        await self._providers.complete_uc.execute(
            job.id,
            started_at=started_at,
            finished_at=finished_at,
            worker_id=self._config.worker_id,
        )

        self._stats.jobs_succeeded += 1

    async def _handle_job_failure(self, job: Job, started_at: datetime, error: Exception) -> None:
        finished_at = datetime.utcnow()
        error_type = error.__class__.__name__ if error else "UnknownError"
        error_message = str(error) if error else "Execution failed"

        logger.error(
            "Job %s failed: %s",
            job.id,
            error_message,
        )

        await self._providers.fail_uc.execute(
            job.id,
            started_at=started_at,
            finished_at=finished_at,
            worker_id=self._config.worker_id,
            error_type=error_type,
            error_message=error_message,
        )

        self._stats.jobs_failed += 1

    async def _handle_job_error(self, job: Job, started_at: datetime, exc: Exception) -> None:
        logger.exception("Unexpected error processing job %s", job.id)

        finished_at = datetime.utcnow()
        error_type = exc.__class__.__name__
        error_message = str(exc)

        await self._providers.fail_uc.execute(
            job.id,
            started_at=started_at,
            finished_at=finished_at,
            worker_id=self._config.worker_id,
            error_type=error_type,
            error_message=error_message,
        )

        self._stats.jobs_failed += 1

    async def _fail_job_with_capability_error(
        self,
        job: Job,
        required_capabilities: list[str],
    ) -> None:
        error_msg = (
            f"Worker {self._config.worker_id} missing required capabilities. "
            f"Required: {required_capabilities}, Available: {self._config.capabilities}"
        )
        now = datetime.utcnow()

        await self._providers.fail_uc.execute(
            job_id=job.id,
            started_at=now,
            finished_at=now,
            worker_id=self._config.worker_id,
            error_type="CapabilityError",
            error_message=error_msg,
        )
