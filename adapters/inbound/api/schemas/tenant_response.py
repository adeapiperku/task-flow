# adapters/inbound/api/schemas/tenant_response.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantResponse(BaseModel):
    """Response model for a tenant."""

    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    class Config:
        orm_mode = True
        from_attributes = True


class TenantListResponse(BaseModel):
    """Response model for a list of tenants."""

    items: List[TenantResponse]
    total: int

    class Config:
        orm_mode = True
        from_attributes = True
