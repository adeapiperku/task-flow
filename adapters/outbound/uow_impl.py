from sqlalchemy.ext.asyncio.session import AsyncSession

from adapters.outbound.db.base import AsyncSessionLocal
from adapters.outbound.db.job_repository_impl import JobRepositorySqlAlchemy
from application.uow import UnitOfWork
from domain.ports.job_repository import JobRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self):
        self._session: AsyncSession | None = None
        self.job_repo: JobRepository | None = None

    async def __aenter__(self):
        self._session = AsyncSessionLocal()
        self.job_repo = JobRepositorySqlAlchemy(self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()
