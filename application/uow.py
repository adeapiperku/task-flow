# application/uow.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, AsyncContextManager

from domain.ports.job_attempt_repository import JobAttemptRepository
from domain.ports.job_repository import JobRepository
from domain.ports.automation_rule_repository import AutomationRuleRepository

T = TypeVar('T', bound=AsyncContextManager)


class UnitOfWork(Protocol):
    """
    Unit of Work abstraction.

    The application layer depends on this interface, not on SQLAlchemy.
    """
    job_repo: JobRepository
    job_attempt_repo: JobAttemptRepository
    automation_rules: AutomationRuleRepository


class UnitOfWorkFactory(Protocol):
    """
    Protocol for Unit of Work factory.
    """
    async def __call__(self) -> AsyncContextManager[UnitOfWork]:
        ...

    async def __aenter__(self) -> "UnitOfWork":
        ...

    async def __aexit__(self, exc_type, exc, tb) -> None:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...
