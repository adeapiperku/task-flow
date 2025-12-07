# worker/runner.py
import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from handlers import HANDLERS

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def dispatch_job(job):
    handler = HANDLERS.get(job.name)
    if handler is None:
        raise RuntimeError(f"No handler found for job '{job.name}'")
    await handler(job.payload)


async def worker_loop(queue: str = "default") -> None:
    worker_id = f"worker-{uuid4()}"

    acquire_uc = AcquireNextJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    complete_uc = CompleteJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    fail_uc = FailJobUseCase(uow_factory=SqlAlchemyUnitOfWork)

    logger.info("Worker %s started on queue '%s'", worker_id, queue)

    while True:
        job = await acquire_uc.execute(queue=queue, worker_id=worker_id)

        if job is None:
            await asyncio.sleep(1.0)
            continue

        logger.info("Worker %s processing job %s (%s)", worker_id, job.id, job.name)

        started_at = datetime.utcnow()
        try:
            await dispatch_job(job)
        except Exception as exc:
            finished_at = datetime.utcnow()
            logger.exception("Job %s failed", job.id)
            await fail_uc.execute(
                job.id,
                started_at=started_at,
                finished_at=finished_at,
                worker_id=worker_id,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
        else:
            finished_at = datetime.utcnow()
            await complete_uc.execute(
                job.id,
                started_at=started_at,
                finished_at=finished_at,
                worker_id=worker_id,
            )
