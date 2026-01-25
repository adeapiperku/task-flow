from typing import List
from uuid import UUID

from domain.models.tenant import Tenant
from adapters.inbound.api.schemas.tenant_response import TenantResponse

class TenantResponseMapper:
    @staticmethod
    def to_response(tenant: Tenant) -> TenantResponse:
        """Convert Tenant domain model to TenantResponse."""
        return TenantResponse(
            id=UUID(tenant.id),
            name=getattr(tenant, 'name', 'Unnamed Tenant'),
            description=getattr(tenant, 'description', None),
            created_at=getattr(tenant, 'created_at', None),
            updated_at=getattr(tenant, 'updated_at', None),
            metadata=getattr(tenant, 'metadata', {}),
            is_active=getattr(tenant, 'is_active', True)
        )

    @staticmethod
    def to_response_list(tenants: List[Tenant]) -> List[TenantResponse]:
        """Convert a list of Tenant domain models to a list of TenantResponse."""
        return [TenantResponseMapper.to_response(tenant) for tenant in tenants]
