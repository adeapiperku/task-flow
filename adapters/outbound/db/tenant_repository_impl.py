# adapters/outbound/db/tenant_repository_impl.py
from typing import List
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.tenant import Tenant
from domain.ports.tenant_repository import TenantRepository as TenantRepositoryPort
from adapters.outbound.db.models.tenant import TenantOrm
from adapters.outbound.db.mappers.tenant_mapper import TenantMapper
from domain.exceptions import RepositoryError

class TenantRepository(TenantRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, tenant_id: str) -> Tenant | None:
        """Retrieve a tenant by ID."""
        try:
            from uuid import UUID
            result = await self._session.get(TenantOrm, UUID(tenant_id))
            if not result:
                return None
            return TenantMapper.to_domain(result)
        except (SQLAlchemyError, ValueError) as exc:
            raise RepositoryError(f"Failed to fetch tenant with id {tenant_id}") from exc

    async def get_all(self) -> list[Tenant]:
        """Retrieve all tenants."""
        try:
            result = await self._session.execute(select(TenantOrm))
            return [TenantMapper.to_domain(orm) for orm in result.scalars().all()]
        except SQLAlchemyError as exc:
            raise RepositoryError("Failed to fetch all tenants") from exc


    async def save(self, tenant: Tenant) -> None:
        """Save a tenant."""
        try:
            orm = TenantMapper.to_orm(tenant)
            self._session.add(orm)
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise RepositoryError(f"Failed to save tenant {tenant.id}") from exc