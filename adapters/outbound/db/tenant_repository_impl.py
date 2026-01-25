from typing import List
from sqlalchemy import select
from adapters.outbound.db.models.tenant import TenantOrm
from adapters.outbound.db.mappers.tenantMapper import TenantMapper
from domain.models.tenant import Tenant


class TenantRepositoryImpl:

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, tenant_id):
        orm = await self.session.get(TenantOrm, tenant_id)
        return TenantMapper.to_domain(orm) if orm else None
        
    async def list_all(self) -> List[Tenant]:
        result = await self.session.execute(select(TenantOrm))
        return [TenantMapper.to_domain(orm) for orm in result.scalars().all()]
