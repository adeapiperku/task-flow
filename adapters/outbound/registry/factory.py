# adapters/outbound/registry/factory.py
"""
Factory for creating job registry instances.

This provides a convenient way to initialize plugin registries.
For DB and hybrid registries, use the UoW pattern directly in dispatch_job.
"""
from __future__ import annotations

from adapters.outbound.registry.job_registry_plugin import PluginJobRegistry
from domain.models.job_definition import JobDefinition


def create_plugin_registry(definitions: dict[str, JobDefinition]) -> PluginJobRegistry:
    """
    Create a plugin-based registry with the given definitions.
    
    This is used for long-lived, in-memory job definitions.
    In production, definitions can be loaded from installed packages via entrypoints.
    """
    return PluginJobRegistry(definitions)


def create_default_registry(definitions: dict[str, JobDefinition]) -> PluginJobRegistry:
    """
    Create a default registry (plugin-based) for simple use cases.
    
    This is the recommended starting point for most deployments.
    For hybrid (plugin + DB) registries, use dispatch_job with UoW pattern.
    """
    return PluginJobRegistry(definitions)

