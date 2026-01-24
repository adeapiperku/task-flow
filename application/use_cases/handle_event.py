from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from application.uow import UnitOfWork
from domain.ports.event_bus import EventBus
from domain.services.automation_engine import AutomationEngine


class HandleEventUseCase:
    """
    Handle incoming events and trigger automation rules.

    This is the application entrypoint for cron/webhook/internal events.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        event_bus: Optional[EventBus] = None,
    ):
        self._uow_factory = uow_factory
        self._event_bus = event_bus

    async def execute(
        self,
        *,
        event_type: str,
        context: Dict[str, Any],
        tenant_id: Optional[str],
    ):
        async with self._uow_factory() as uow:
            engine = AutomationEngine(
                rule_repository=uow.automation_rules,
                job_repository=uow.job_repo,
            )
            jobs = await engine.handle_event(
                event_type=event_type,
                context=context,
                tenant_id=tenant_id,
            )

            if self._event_bus:
                for job in jobs:
                    await self._event_bus.publish_job_created(job)

            return jobs
