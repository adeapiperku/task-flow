# adapters/inbound/api/routers/tenants.py
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.inbound.api.schemas.tenant_response import TenantResponse, TenantListResponse
from adapters.inbound.api.mappers.tenant_mapper import TenantResponseMapper
from application.use_cases.get_all_tenants import GetAllTenantsUseCase
from domain.exceptions import RepositoryError

router = APIRouter(tags=["tenants"])

def get_get_all_tenants_use_case() -> GetAllTenantsUseCase:
    return GetAllTenantsUseCase(uow_factory=SqlAlchemyUnitOfWork)

@router.get("", response_model=TenantListResponse)
async def list_tenants(
    use_case: GetAllTenantsUseCase = Depends(get_get_all_tenants_use_case),
):
    """
    List all tenants.
    
    Returns a paginated list of all tenants in the system.
    """
    try:
        tenants = await use_case.execute()
        tenant_responses = TenantResponseMapper.to_response_list(tenants)
        return {
            "items": tenant_responses,
            "total": len(tenant_responses)
        }
    except RepositoryError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch tenants: {str(e)}"
        )