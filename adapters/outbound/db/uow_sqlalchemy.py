# adapters/outbound/db/uow_sqlalchemy.py
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.db.base import AsyncSessionLocal
from adapters.outbound.db.job_attempt_repository_impl import JobAttemptRepositorySqlAlchemy
from adapters.outbound.db.job_repository_impl import JobRepositorySqlAlchemy
from adapters.outbound.db.automation_rule_repository_impl import SqlAlchemyAutomationRuleRepository
from application.uow import UnitOfWork
from domain.ports.job_repository import JobRepository
from domain.ports.job_attempt_repository import JobAttemptRepository
from domain.ports.automation_rule_repository import AutomationRuleRepository
from domain.ports.tenant_repository import TenantRepository as TenantRepositoryPort
from adapters.outbound.db.tenant_repository_impl import TenantRepository as TenantRepositoryImpl


class SqlAlchemyUnitOfWork(UnitOfWork):
    """
    SQLAlchemy-based Unit of Work.

    Responsibilities:
    - create/close session
    - manage transaction (commit/rollback)
    - provide repositories bound to this session
    """

    def __init__(self):
        self._session: AsyncSession | None = None
        self.job_repo: JobRepository | None = None
        self.job_attempt_repo: JobAttemptRepository | None = None
        self.automation_rules: AutomationRuleRepository | None = None
        self._tenant_repo: TenantRepositoryPort | None = None

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = AsyncSessionLocal()
        self.job_repo = JobRepositorySqlAlchemy(self._session)
        self.job_attempt_repo = JobAttemptRepositorySqlAlchemy(self._session)
        self.automation_rules = SqlAlchemyAutomationRuleRepository(self._session)
        self._tenant_repo = TenantRepositoryImpl(self._session)

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()

    @property
    def tenant_repo(self) -> TenantRepository:
        if self._tenant_repo is None:
            raise ValueError("Tenant repository not initialized")
        return self._tenant_repo

    async def commit(self) -> None:
        if self._session:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session:
            await self._session.rollback()
