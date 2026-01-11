# adapters/outbound/registry/job_registry_hybrid.py
from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.outbound.registry.job_registry_db import DbJobRegistry
from adapters.outbound.registry.job_registry_plugin import PluginJobRegistry
from domain.exceptions import HandlerNotFoundError, JobDefinitionNotFoundError
from domain.models.job_definition import JobDefinition
from domain.ports.job_registry import JobRegistry

logger = logging.getLogger(__name__)


class HybridJobRegistry(JobRegistry):
    """
    Hybrid job registry that combines plugin and database sources.
    
    Strategy:
    1. First check plugin registry (fast, in-memory)
    2. If not found, check database registry
    3. Database definitions can override plugin definitions
    
    This allows:
    - Default job definitions shipped with the worker (plugin)
    - Custom/updated definitions managed via API (database)
    """

    def __init__(
        self,
        plugin_registry: PluginJobRegistry,
        db_registry: DbJobRegistry,
        prefer_db: bool = False,
    ):
        """
        Initialize the hybrid registry.
        
        Args:
            plugin_registry: Plugin-based registry (in-memory definitions)
            db_registry: Database-based registry
            prefer_db: If True, database definitions override plugin ones
        """
        self._plugin_registry = plugin_registry
        self._db_registry = db_registry
        self._prefer_db = prefer_db

    async def get_definition(self, name: str) -> JobDefinition | None:
        """
        Get definition from plugin or database.
        
        If prefer_db=True, database takes precedence.
        Otherwise, plugin is checked first (faster).
        """
        if self._prefer_db:
            # Try DB first, fallback to plugin
            definition = await self._db_registry.get_definition(name)
            if definition is not None:
                return definition
            return await self._plugin_registry.get_definition(name)
        else:
            # Try plugin first, fallback to DB
            definition = await self._plugin_registry.get_definition(name)
            if definition is not None:
                return definition
            return await self._db_registry.get_definition(name)

    async def resolve_handler(self, handler_ref: str) -> Callable:
        """
        Resolve handler - both registries use the same importlib mechanism.
        Try plugin first, then DB.
        """
        try:
            return await self._plugin_registry.resolve_handler(handler_ref)
        except HandlerNotFoundError:
            return await self._db_registry.resolve_handler(handler_ref)

    async def get_handler(self, job_name: str) -> Callable:
        """Get definition and resolve handler."""
        definition = await self.get_definition(job_name)
        if definition is None:
            raise JobDefinitionNotFoundError(f"Job definition '{job_name}' not found")
        
        return await self.resolve_handler(definition.handler_ref)


