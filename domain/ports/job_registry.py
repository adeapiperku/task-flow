# domain/ports/job_registry.py
from __future__ import annotations

from typing import Callable, Protocol

from domain.models.job_definition import JobDefinition


class JobRegistry(Protocol):
    """
    Port for resolving job definitions and their handlers.
    
    The domain layer depends on this protocol, not on any concrete implementation.
    This allows workers to execute jobs without hardcoded handler mappings.
    
    Implementations can:
    - Load definitions from plugins (entrypoints/importlib)
    - Load definitions from database
    - Combine both (hybrid approach)
    """

    async def get_definition(self, name: str) -> JobDefinition | None:
        """
        Retrieve a job definition by name.
        
        Args:
            name: The job definition name (e.g., "email.send")
            
        Returns:
            JobDefinition if found, None otherwise
        """
        ...

    async def resolve_handler(self, handler_ref: str) -> Callable:
        """
        Resolve a handler function from a handler reference string.
        
        Handler references follow the format: "module.path:function_name"
        Example: "taskflow_jobs.email:send_email"
        
        Args:
            handler_ref: The handler reference string
            
        Returns:
            The callable handler function
            
        Raises:
            HandlerNotFoundError: If the handler cannot be resolved
        """
        ...

    async def get_handler(self, job_name: str) -> Callable:
        """
        Convenience method: get definition and resolve handler in one call.
        
        Args:
            job_name: The job definition name
            
        Returns:
            The callable handler function
            
        Raises:
            JobDefinitionNotFoundError: If definition not found
            HandlerNotFoundError: If handler cannot be resolved
        """
        ...


