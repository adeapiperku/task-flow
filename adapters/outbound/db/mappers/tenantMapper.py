from adapters.outbound.db.models.tenant import TenantOrm
from domain.models.tenant import Tenant


class TenantMapper:

    @staticmethod
    def to_domain(orm: TenantOrm) -> Tenant:
        return Tenant(
            id=orm.id,
            name=orm.name,
            max_running_jobs=orm.max_running_jobs,
            active=orm.active,
        )

    @staticmethod
    def to_orm(tenant: Tenant) -> TenantOrm:
        return TenantOrm(
            id=tenant.id,
            name=tenant.name,
            max_running_jobs=tenant.max_running_jobs,
            active=tenant.active,
        )
