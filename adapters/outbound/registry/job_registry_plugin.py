# adapters/outbound/registry/job_registry_plugin.py
from __future__ import annotations

import importlib
import logging
from typing import Callable

from domain.exceptions import HandlerNotFoundError, JobDefinitionNotFoundError
from domain.models.job_definition import JobDefinition
from domain.ports.job_registry import JobRegistry

logger = logging.getLogger(__name__)


class PluginJobRegistry(JobRegistry):
    """
    Plugin-based job registry that resolves handlers via importlib.
    
    This adapter loads job definitions from Python modules using handler references.
    Handlers are resolved dynamically at runtime using importlib.
    
    This is the "plugin" approach where job code lives in separate packages.
    """

    def __init__(self, definitions: dict[str, JobDefinition]):
        """
        Initialize the plugin registry with a dictionary of job definitions.
        
        Args:
            definitions: Dictionary mapping job names to JobDefinition instances
        """
        self._definitions: dict[str, JobDefinition] = definitions
        self._handler_cache: dict[str, Callable] = {}

    async def get_definition(self, name: str) -> JobDefinition | None:
        """Retrieve a job definition by name."""
        return self._definitions.get(name)

    async def resolve_handler(self, handler_ref: str) -> Callable:
        """
        Resolve a handler function from a handler reference.
        
        Format: "module.path:function_name"
        Example: "handlers.email:send_email"
        
        Handlers are cached after first resolution.
        """
        if handler_ref in self._handler_cache:
            return self._handler_cache[handler_ref]

        try:
            module_path, function_name = handler_ref.split(":", 1)
        except ValueError:
            raise HandlerNotFoundError(
                f"Invalid handler reference format: {handler_ref}. "
                "Expected format: 'module.path:function_name'"
            )

        try:
            module = importlib.import_module(module_path)
            handler = getattr(module, function_name)
            
            if not callable(handler):
                raise HandlerNotFoundError(
                    f"Handler reference '{handler_ref}' does not point to a callable"
                )
            
            self._handler_cache[handler_ref] = handler
            logger.debug("Resolved handler: %s -> %s", handler_ref, handler)
            return handler
            
        except ImportError as exc:
            raise HandlerNotFoundError(
                f"Could not import module '{module_path}' for handler '{handler_ref}'"
            ) from exc
        except AttributeError as exc:
            raise HandlerNotFoundError(
                f"Function '{function_name}' not found in module '{module_path}'"
            ) from exc

    async def get_handler(self, job_name: str) -> Callable:
        """Get definition and resolve handler in one call."""
        definition = await self.get_definition(job_name)
        if definition is None:
            raise JobDefinitionNotFoundError(f"Job definition '{job_name}' not found")
        
        return await self.resolve_handler(definition.handler_ref)


