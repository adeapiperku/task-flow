# worker/runner.py
import asyncio
import logging
from uuid import uuid4

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def process_image(payload: dict):
    image_id = payload.get("image_id")
    logger.info("Pretend processing image %s", image_id)
    await asyncio.sleep(0.5)


HANDLERS = {
    "process-image": process_image,
}


async def dispatch_job(job):
    handler = HANDLERS.get(job.name)
    if handler is None:
        raise RuntimeError(f"No handler for job {job.name}")

    return await handler(job.payload)


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

        try:
            await dispatch_job(job)
        except Exception:
            logger.exception("Job %s failed", job.id)
            await fail_uc.execute(job.id)
        else:
            await complete_uc.execute(job.id)


if __name__ == "__main__":
    asyncio.run(worker_loop(queue="media"))
