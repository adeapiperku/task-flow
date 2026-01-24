# adapters/outbound/db/job_repository_impl.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func, and_, or_, cast, String, exists
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from adapters.outbound.db.mappers.job_mapper import JobMapper
from adapters.outbound.db.models import JobOrm, QueueOrm, TenantOrm
from domain.models.job import Job, JobState
from domain.ports.job_repository import JobRepository
from domain.exceptions import JobAlreadyExistsError, RepositoryError

import logging

logger = logging.getLogger(__name__)

class JobRepositorySqlAlchemy(JobRepository):
    """
    SQLAlchemy implementation of JobRepository.
    This class does NOT manage sessions or transactions.

    Session is provided by the Unit of Work.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def insert(self, job: Job) -> Job:
        orm = JobMapper.to_orm(job)
        self._session.add(orm)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise JobAlreadyExistsError("Job already exists") from exc
        except SQLAlchemyError as exc:
            raise RepositoryError("Database operation failed") from exc

        return JobMapper.to_domain(orm)

    async def get_by_id(self, job_id: UUID) -> Job | None:
        try:
            orm = await self._session.get(JobOrm, job_id)
        except SQLAlchemyError as exc:
            raise RepositoryError("Database operation failed") from exc

        if orm is None:
            return None

        return JobMapper.to_domain(orm)

    async def update(self, job: Job) -> Job:
        """
        Simple v0 implementation:
        - load ORM row
        - copy fields from domain
        - flush
        """
        try:
            orm = await self._session.get(JobOrm, job.id)
            if orm is None:
                raise RepositoryError(f"Job {job.id} not found for update")

            JobMapper.update_orm_from_domain(job, orm)
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError("Database operation failed") from exc

        return JobMapper.to_domain(orm)

    async def acquire_next_due_job(
            self,
            *,
            queue: str,
            now: datetime,
            worker_id: str,
            visibility_timeout_s: int = 300,
    ) -> Job | None:
        """
        Atomically select and lock the next runnable job for a worker.
        """
        from datetime import timedelta
        
        try:
            logger.debug(
                "repo.acquire_next_due_job: queue=%s worker_id=%s now=%s",
                queue,
                worker_id,
                now,
            )
            # Enforce queue-level concurrency limits when configured
            queue_stmt = select(QueueOrm.max_concurrency, QueueOrm.active).where(
                QueueOrm.name == queue
            )
            queue_result = await self._session.execute(queue_stmt)
            queue_row = queue_result.first()
            if queue_row:
                max_concurrency, active = queue_row
                if active is False:
                    logger.info(
                        "repo.acquire_next_due_job: queue inactive queue=%s",
                        queue,
                    )
                    return None
                running_in_queue = await self._session.execute(
                    select(func.count())
                    .select_from(JobOrm)
                    .where(
                        JobOrm.queue == queue,
                        JobOrm.state == JobState.RUNNING.value,
                        JobOrm.archived.is_(False),
                    )
                )
                if running_in_queue.scalar_one() >= max_concurrency:
                    logger.info(
                        "repo.acquire_next_due_job: queue concurrency limit reached queue=%s",
                        queue,
                    )
                    return None

            running_jobs = aliased(JobOrm)
            running_count = (
                select(func.count())
                .select_from(running_jobs)
                .where(
                    running_jobs.state == JobState.RUNNING.value,
                    running_jobs.tenant_id == JobOrm.tenant_id,
                    running_jobs.archived.is_(False),
                )
                .correlate(JobOrm)
                .scalar_subquery()
            )

            stmt = (
                select(JobOrm)
                .where(
                    JobOrm.queue == queue,
                    JobOrm.archived.is_(False),
                    JobOrm.state.in_(
                        [JobState.PENDING.value, JobState.SCHEDULED.value]
                    ),
                    (
                        JobOrm.next_run_at.is_(None)
                        | (JobOrm.next_run_at <= func.now())
                    ),
                    or_(
                        JobOrm.tenant_id.is_(None),
                        exists(
                            select(1).where(
                                cast(TenantOrm.id, String) == JobOrm.tenant_id,
                                TenantOrm.active.is_(True),
                                running_count < TenantOrm.max_running_jobs,
                            )
                        ),
                    ),
                )
                .order_by(
                    JobOrm.priority.desc(),
                    JobOrm.created_at.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            )

            result = await self._session.execute(stmt)
            orm: JobOrm | None = result.scalar_one_or_none()
            if orm is None:
                logger.debug("repo.acquire_next_due_job: no runnable job found")
                tenant_limit_stmt = (
                    select(
                        JobOrm.tenant_id,
                        func.count().label("running_count"),
                        TenantOrm.max_running_jobs,
                    )
                    .join(
                        TenantOrm,
                        cast(TenantOrm.id, String) == JobOrm.tenant_id,
                    )
                    .where(
                        JobOrm.queue == queue,
                        JobOrm.state == JobState.RUNNING.value,
                        JobOrm.archived.is_(False),
                        TenantOrm.active.is_(True),
                    )
                    .group_by(JobOrm.tenant_id, TenantOrm.max_running_jobs)
                    .having(func.count() >= TenantOrm.max_running_jobs)
                    .limit(1)
                )
                tenant_limit_row = (await self._session.execute(tenant_limit_stmt)).first()
                if tenant_limit_row:
                    tenant_id, running_count_val, max_running_jobs = tenant_limit_row
                    logger.info(
                        "repo.acquire_next_due_job: tenant concurrency limit reached tenant_id=%s running=%s limit=%s",
                        tenant_id,
                        running_count_val,
                        max_running_jobs,
                    )
                if logger.isEnabledFor(logging.DEBUG):
                    base_filters = [
                        JobOrm.queue == queue,
                        JobOrm.archived.is_(False),
                    ]
                    state_filters = base_filters + [
                        JobOrm.state.in_(
                            [JobState.PENDING.value, JobState.SCHEDULED.value]
                        )
                    ]
                    time_filters = state_filters + [
                        (
                            JobOrm.next_run_at.is_(None)
                            | (JobOrm.next_run_at <= func.now())
                        )
                    ]
                    tenant_filters = time_filters + [
                        or_(
                            JobOrm.tenant_id.is_(None),
                            exists(
                                select(1).where(
                                    cast(TenantOrm.id, String) == JobOrm.tenant_id,
                                    TenantOrm.active.is_(True),
                                    running_count < TenantOrm.max_running_jobs,
                                )
                            ),
                        )
                    ]

                    total_count = await self._session.execute(
                        select(func.count()).select_from(JobOrm).where(*base_filters)
                    )
                    state_count = await self._session.execute(
                        select(func.count()).select_from(JobOrm).where(*state_filters)
                    )
                    time_count = await self._session.execute(
                        select(func.count()).select_from(JobOrm).where(*time_filters)
                    )
                    tenant_count = await self._session.execute(
                        select(func.count()).select_from(JobOrm).where(*tenant_filters)
                    )
                    logger.debug(
                        "repo.acquire_next_due_job: counts total=%s state=%s time=%s tenant=%s",
                        total_count.scalar_one(),
                        state_count.scalar_one(),
                        time_count.scalar_one(),
                        tenant_count.scalar_one(),
                    )
                return None

            # Use domain method to acquire lease
            job = JobMapper.to_domain(orm)
            leased_job = job.acquire_lease(
                worker_id=worker_id,
                visibility_timeout_s=visibility_timeout_s,
                now=now,
            )
            
            # Update ORM from leased job
            JobMapper.update_orm_from_domain(leased_job, orm)

            await self._session.flush()

            logger.info(
                "repo.acquire_next_due_job: leased job_id=%s name=%s lease_expires_at=%s",
                leased_job.id,
                leased_job.name,
                leased_job.lease_expires_at,
            )
            return leased_job

        except SQLAlchemyError as exc:
            raise RepositoryError("Database operation failed") from exc

    async def find_expired_running_jobs(
        self,
        *,
        cutoff: datetime,
        limit: int = 100,
    ) -> list[Job]:
        """
        Find RUNNING jobs with expired leases.
        """
        try:
            stmt = (
                select(JobOrm)
                .where(
                    JobOrm.state == JobState.RUNNING.value,
                    JobOrm.lease_expires_at.is_not(None),
                    JobOrm.lease_expires_at <= cutoff,
                    JobOrm.archived.is_(False),
                )
                .order_by(JobOrm.lease_expires_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            result = await self._session.execute(stmt)
            orms = result.scalars().all()
            return [JobMapper.to_domain(orm) for orm in orms]
        except SQLAlchemyError as exc:
            raise RepositoryError("Database operation failed") from exc

    async def get_all(self) -> list[Job]:
        """Retrieve all jobs."""
        try:
            result = await self._session.execute(select(JobOrm))
            jobs = [JobMapper.to_domain(orm) for orm in result.scalars().all()]
            return jobs
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to fetch all jobs") from exc