from application.uow import UnitOfWork


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
