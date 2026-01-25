from datetime import datetime
from uuid import UUID

from adapters.outbound.db.models.tenant import TenantOrm
from domain.models.tenant import Tenant

class TenantMapper:
    @staticmethod
    def to_domain(orm: TenantOrm) -> Tenant:
        """Convert TenantOrm to Tenant domain model."""
        return Tenant(
            id=str(orm.id),
            max_running_jobs=getattr(orm, 'max_running_jobs', 5),  # Default to 5 if not set
            weight=getattr(orm, 'weight', 1),  # Default to 1 if not set
            created_at=getattr(orm, 'created_at', datetime.utcnow()),
            updated_at=getattr(orm, 'updated_at', datetime.utcnow()),
        )

    @staticmethod
    def to_orm(tenant: Tenant) -> TenantOrm:
        """Convert Tenant domain model to TenantOrm."""
        return TenantOrm(
            id=UUID(tenant.id),
            name=tenant.name,
            max_running_jobs=tenant.max_running_jobs,
            active=True
        )
