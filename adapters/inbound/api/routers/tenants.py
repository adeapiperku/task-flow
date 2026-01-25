from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from adapters.outbound.db.base import AsyncSessionLocal

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
from domain.ports.tenant_repository import TenantRepository
from adapters.outbound.db.tenant_repository_impl import TenantRepositoryImpl
from adapters.inbound.api.schemas.tenant_response import TenantResponse
from domain.models.tenant import Tenant

router = APIRouter()

def get_tenant_repository(session: AsyncSession = Depends(get_db)) -> TenantRepository:
    return TenantRepositoryImpl(session)

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    repository: TenantRepository = Depends(get_tenant_repository)
):
    """List all tenants"""
    tenants = await repository.list_all()
    return tenants

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    repository: TenantRepository = Depends(get_tenant_repository)
):
    """Get a specific tenant by ID"""
    tenant = await repository.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
