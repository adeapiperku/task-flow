from __future__ import annotations

from typing import Callable, Optional

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.outbound.registry.initializers import create_registry_from_handlers
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from application.use_cases.heartbeat_job import HeartbeatJobUseCase
from domain.ports.job_registry import JobRegistry

from .registry import RegistryManager


class WorkerProviders:
    """
    Provider container for worker dependencies.

    Keeps worker initialization small and allows swapping dependencies in tests.
    """

    def __init__(
        self,
        *,
        uow_factory: Callable[[], any] | None,
        plugin_registry: JobRegistry | None,
        prefer_db: bool,
    ):
        self.uow_factory = uow_factory or SqlAlchemyUnitOfWork
        self.plugin_registry = plugin_registry or self._create_default_registry()
        self.registry_manager = RegistryManager(
            plugin_registry=self.plugin_registry,
            uow_factory=self.uow_factory,
            prefer_db=prefer_db,
        )

        self.acquire_uc = AcquireNextJobUseCase(uow_factory=self.uow_factory)
        self.complete_uc = CompleteJobUseCase(uow_factory=self.uow_factory)
        self.fail_uc = FailJobUseCase(uow_factory=self.uow_factory)
        self.heartbeat_uc = HeartbeatJobUseCase(uow_factory=self.uow_factory)

    @staticmethod
    def _create_default_registry() -> JobRegistry:
        from handlers import HANDLERS
        return create_registry_from_handlers(HANDLERS)
