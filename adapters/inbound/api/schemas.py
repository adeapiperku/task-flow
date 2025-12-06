# adapters/inbound/api/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from domain.models.job import Job


class JobResponse(BaseModel):
    id: UUID
    name: str
    queue: str
    tenant_id: Optional[str]
    state: str
    priority: int
    created_at: datetime
    scheduled_at: Optional[datetime]

    @classmethod
    def from_domain(cls, job: Job) -> "JobResponse":
        return cls(
            id=job.id,
            name=job.name,
            queue=job.queue,
            tenant_id=job.tenant_id,
            state=job.state.value,
            priority=job.priority,
            created_at=job.created_at,
            scheduled_at=job.scheduled_at,
        )
