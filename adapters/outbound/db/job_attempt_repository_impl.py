# adapters/outbound/db/job_attempt_repository_impl.py
from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from adapters.outbound.db.mappers.job_attempt_mapper import JobAttemptMapper
from adapters.outbound.db.models import JobAttemptOrm
from domain.models.job_attempt import JobAttempt
from domain.ports.job_attempt_repository import JobAttemptRepository
from domain.exceptions import RepositoryError


class JobAttemptRepositorySqlAlchemy(JobAttemptRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def insert(self, attempt: JobAttempt) -> JobAttempt:
        orm = JobAttemptMapper.to_orm(attempt)
        self._session.add(orm)
        try:
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to insert job attempt") from exc
        return JobAttemptMapper.to_domain(orm)

    async def list_for_job(self, job_id: UUID) -> List[JobAttempt]:
        try:
            result = await self._session.execute(
                select(JobAttemptOrm).where(JobAttemptOrm.job_id == job_id).order_by(
                    JobAttemptOrm.attempt_number.asc()
                )
            )
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to load job attempts") from exc

        orms = result.scalars().all()
        return [JobAttemptMapper.to_domain(o) for o in orms]
