# adapters/outbound/db/job_repository_impl.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from adapters.outbound.db.mappers.job_mapper import JobMapper
from domain.models.job import Job
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
