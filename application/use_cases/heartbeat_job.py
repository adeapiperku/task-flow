# application/use_cases/heartbeat_job.py
from __future__ import annotations

from typing import Callable
from uuid import UUID

from application.uow import UnitOfWork
from domain.exceptions import NotFoundError
from domain.models.job import Job


class HeartbeatJobUseCase:
    """
    Extend the lease on a running job (heartbeat).
    
    This prevents the job from being reclaimed if the worker is still processing it.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(
        self,
        job_id: UUID,
        worker_id: str,
        visibility_timeout_s: int,
    ) -> Job:
        """
        Extend the lease expiration time for a running job.
        
        Args:
            job_id: Job ID to heartbeat
            visibility_timeout_s: New visibility timeout in seconds
            
        Returns:
            Updated job with extended lease
        """
        async with self._uow_factory() as uow:
            job = await uow.job_repo.get_by_id(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} not found")

            # Only heartbeat if job is RUNNING and we own it
            if job.state.value != "RUNNING":
                return job
            if job.locked_by != worker_id:
                return job

            updated = job.extend_lease(visibility_timeout_s=visibility_timeout_s)
            stored_job = await uow.job_repo.update(updated)
            return stored_job

