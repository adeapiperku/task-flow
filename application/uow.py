# application/uow.py
from __future__ import annotations

from typing import Protocol

from domain.ports.job_repository import JobRepository


class UnitOfWork(Protocol):
    """
    Unit of Work abstraction.

    The application layer depends on this interface, not on SQLAlchemy.
    """

    job_repo: JobRepository

    async def __aenter__(self) -> "UnitOfWork":
        ...

    async def __aexit__(self, exc_type, exc, tb) -> None:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...
