# application/dto/schedule_job_command.py
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ScheduleJobCommand(BaseModel):
    """
    Command object representing a request to schedule a new job.
    """

    name: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any] = Field(default_factory=dict)

    queue: str = Field(default="default", min_length=1, max_length=64)
    tenant_id: Optional[str] = Field(default=None, max_length=64)
    priority: int = Field(default=0, ge=-32_768, le=32_767)

    scheduled_at: Optional[datetime] = None
    max_attempts: int = Field(default=3, ge=1, le=100)

    id: Optional[UUID] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()
