from typing import Protocol
from domain.models.tenant import Tenant


class TenantRepository(Protocol):
    async def get_by_id(self, tenant_id: str) -> Tenant | None: ...
    async def save(self, tenant: Tenant) -> None: ...
