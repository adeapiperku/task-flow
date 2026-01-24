from sqlalchemy.ext.asyncio.session import AsyncSession

from adapters.outbound.db.base import AsyncSessionLocal
from adapters.outbound.db.job_repository_impl import JobRepositorySqlAlchemy
from adapters.outbound.db.job_attempt_repository_impl import JobAttemptRepositorySqlAlchemy
from application.uow import UnitOfWork
from domain.ports.job_repository import JobRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self):
        self._session: AsyncSession | None = None
        self.job_repo: JobRepository | None = None
        self.job_attempt_repo = None

    async def __aenter__(self):
        self._session = AsyncSessionLocal()
        self.job_repo = JobRepositorySqlAlchemy(self._session)
        self.job_attempt_repo = JobAttemptRepositorySqlAlchemy(self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()

    async def commit(self) -> None:
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()
