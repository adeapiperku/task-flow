from adapters.outbound.db import TenantOrm
from adapters.outbound.db.mappers.tenantMapper import TenantMapper


class TenantRepositoryImpl:

    def __init__(self, session):
        self.session = session

    async def get_by_id(self, tenant_id):
        orm = await self.session.get(TenantOrm, tenant_id)
        return TenantMapper.to_domain(orm) if orm else None
