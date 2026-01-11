# adapters/outbound/registry/initializers.py
"""
Helpers to initialize job registries from existing handler patterns.
"""
from __future__ import annotations

from domain.models.job_definition import JobDefinition
from domain.ports.job_registry import JobRegistry
from adapters.outbound.registry.job_registry_plugin import PluginJobRegistry


def create_registry_from_handlers(
    handlers: dict[str, any],
    default_timeout_s: int = 300,
    default_max_attempts: int = 3,
    default_visibility_timeout_s: int = 300,
) -> PluginJobRegistry:
    """
    Create a plugin registry from a dictionary of handler functions.
    
    This is a migration helper to convert from the old HANDLERS dict pattern
    to the new JobRegistry pattern.
    
    Args:
        handlers: Dictionary mapping job names to handler functions
        default_timeout_s: Default timeout for all jobs
        default_max_attempts: Default max attempts for all jobs
        default_visibility_timeout_s: Default visibility timeout for all jobs
        
    Returns:
        PluginJobRegistry initialized with JobDefinitions derived from handlers
    """
    definitions: dict[str, JobDefinition] = {}
    
    for job_name, handler in handlers.items():
        # Extract module and function name from handler
        handler_module = handler.__module__
        handler_name = handler.__name__
        handler_ref = f"{handler_module}:{handler_name}"
        
        definition = JobDefinition(
            name=job_name,
            handler_ref=handler_ref,
            execution_mode="python_async",
            timeout_s=default_timeout_s,
            max_attempts=default_max_attempts,
            backoff_policy={},
            input_schema={},
            resource_profile={},
            capabilities=[],
            visibility_timeout_s=default_visibility_timeout_s,
            version=1,
        )
        definitions[job_name] = definition
    
    return PluginJobRegistry(definitions)


