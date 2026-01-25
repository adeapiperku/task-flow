# application/use_cases/get_all_tenants.py
from typing import List
from uuid import UUID

from application.uow import UnitOfWork, UnitOfWorkFactory
from domain.models.tenant import Tenant
from domain.ports.tenant_repository import TenantRepository

class GetAllTenantsUseCase:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self) -> List[Tenant]:
        async with self.uow_factory() as uow:
            tenant_repo = uow.tenant_repo
            if tenant_repo is None:
                raise ValueError("Tenant repository not initialized")
            return await tenant_repo.get_all()