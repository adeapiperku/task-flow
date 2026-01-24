from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from adapters.inbound.api.schemas.job_response import JobResponse
from adapters.outbound.broker.logging_event_bus import LoggingEventBus
from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from application.use_cases.handle_event import HandleEventUseCase

router = APIRouter(prefix="/events", tags=["events"])


class EventPayload(BaseModel):
    context: Dict[str, Any] = {}
    tenant_id: Optional[str] = None


def get_handle_event_use_case() -> HandleEventUseCase:
    return HandleEventUseCase(
        uow_factory=SqlAlchemyUnitOfWork,
        event_bus=LoggingEventBus(),
    )


@router.post("/{event_type}", response_model=List[JobResponse], status_code=201)
async def handle_event(
    event_type: str,
    payload: EventPayload,
    use_case: HandleEventUseCase = Depends(get_handle_event_use_case),
):
    jobs = await use_case.execute(
        event_type=event_type,
        context=payload.context,
        tenant_id=payload.tenant_id,
    )
    return [JobResponse.from_domain(job) for job in jobs]
