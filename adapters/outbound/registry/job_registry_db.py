# adapters/outbound/registry/job_registry_db.py
from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from adapters.outbound.db.mappers.job_definition_mapper import JobDefinitionMapper
from adapters.outbound.db.models import JobDefinitionOrm
from domain.exceptions import HandlerNotFoundError, JobDefinitionNotFoundError, RepositoryError
from domain.models.job_definition import JobDefinition
from domain.ports.job_registry import JobRegistry

logger = logging.getLogger(__name__)


class DbJobRegistry(JobRegistry):
    """
    Database-based job registry that loads definitions from JobDefinitionOrm.
    
    This adapter fetches job definitions from the database and resolves handlers
    using importlib (same as plugin registry).
    
    This is useful when job definitions are managed via API/DB rather than
    hardcoded in the worker.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the DB registry with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._handler_cache: dict[str, Callable] = {}
        self._definition_cache: dict[str, JobDefinition] = {}

    async def get_definition(self, name: str) -> JobDefinition | None:
        """Retrieve a job definition from the database."""
        # Check cache first
        if name in self._definition_cache:
            return self._definition_cache[name]

        try:
            stmt = select(JobDefinitionOrm).where(JobDefinitionOrm.name == name)
            result = await self._session.execute(stmt)
            orm: JobDefinitionOrm | None = result.scalar_one_or_none()
            
            if orm is None:
                return None

            definition = JobDefinitionMapper.to_domain(orm)
            self._definition_cache[name] = definition
            return definition
            
        except SQLAlchemyError as exc:
            logger.error("Database error loading job definition '%s': %s", name, exc)
            raise RepositoryError("Failed to load job definition") from exc

    async def resolve_handler(self, handler_ref: str) -> Callable:
        """
        Resolve a handler function from a handler reference.
        
        Uses importlib to dynamically load the handler.
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
            import importlib
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
