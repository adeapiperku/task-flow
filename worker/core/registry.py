"""Registry-related functionality for the worker."""
from typing import Optional

from domain.ports.job_registry import JobRegistry


class RegistryManager:
    """Manages job registries and handler resolution."""
    
    def __init__(self, plugin_registry: JobRegistry, uow_factory, prefer_db: bool = True):
        """Initialize with plugin registry and UoW factory."""
        self.plugin_registry = plugin_registry
        self.uow_factory = uow_factory
        self.prefer_db = prefer_db
    
    async def get_hybrid_registry(self):
        """Create a new hybrid registry instance."""
        from adapters.outbound.registry.job_registry_db import DbJobRegistry
        from adapters.outbound.registry.job_registry_hybrid import HybridJobRegistry
        
        async with self.uow_factory() as uow:
            db_registry = DbJobRegistry(uow._session)
            return HybridJobRegistry(
                plugin_registry=self.plugin_registry,
                db_registry=db_registry,
                prefer_db=self.prefer_db,
            )
    
    async def get_job_definition(self, job_name: str):
        """Get job definition from registry."""
        registry = await self.get_hybrid_registry()
        return await registry.get_definition(job_name)
