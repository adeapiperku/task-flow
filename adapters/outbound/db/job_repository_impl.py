# adapters/outbound/db/job_repository_impl.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from adapters.outbound.db.mappers.job_mapper import JobMapper
from adapters.outbound.db.models import JobOrm
from domain.models.job import Job, JobState
from domain.ports.job_repository import JobRepository
from domain.exceptions import JobAlreadyExistsError, RepositoryError

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
    ) -> Job | None:
        """
        Atomically select and lock the next runnable job for a worker.
        """
        try:
            stmt = (
                select(JobOrm)
                .where(
                    JobOrm.queue == queue,
                    JobOrm.archived.is_(False),
                    JobOrm.state.in_(
                        [JobState.PENDING.value, JobState.SCHEDULED.value]
                    ),
                    (JobOrm.next_run_at.is_(None) | (JobOrm.next_run_at <= now)),
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
                return None

            orm.locked_by = worker_id
            orm.locked_at = now
            orm.state = JobState.RUNNING.value
            orm.last_run_at = now
            orm.attempts = (orm.attempts or 0) + 1

            await self._session.flush()

            return JobMapper.to_domain(orm)

        except SQLAlchemyError as exc:
            raise RepositoryError("Database operation failed") from exc

