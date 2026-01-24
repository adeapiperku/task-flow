# application/use_cases/reclaim_expired_jobs.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from application.uow import UnitOfWork
from domain.models.job import Job, JobState


class ReclaimExpiredJobsUseCase:
    """
    Reclaim jobs that have expired leases (worker died or crashed).
    
    This should be run periodically (e.g., every 30 seconds) to find jobs
    stuck in RUNNING state with expired leases and requeue them.
    """

    def __init__(self, uow_factory: Callable[[], UnitOfWork]):
        self._uow_factory = uow_factory

    async def execute(
        self,
        *,
        grace_period_s: int = 60,
        max_reclaim: int = 100,
    ) -> list[Job]:
        """
        Reclaim expired jobs.
        
        Args:
            grace_period_s: Additional grace period beyond lease expiration
            max_reclaim: Maximum number of jobs to reclaim in one run
            
        Returns:
            List of reclaimed jobs
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=grace_period_s)
        
        async with self._uow_factory() as uow:
            expired_jobs = await uow.job_repo.find_expired_running_jobs(
                cutoff=cutoff,
                limit=max_reclaim,
            )
            reclaimed: list[Job] = []
            for job in expired_jobs:
                requeued = job._replace(
                    state=JobState.SCHEDULED,
                    locked_by=None,
                    locked_at=None,
                    lease_expires_at=None,
                )
                stored = await uow.job_repo.update(requeued)
                reclaimed.append(stored)

            return reclaimed

