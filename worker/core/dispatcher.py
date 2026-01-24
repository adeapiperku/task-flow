"""Job dispatching and execution logic."""
import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from domain.exceptions import HandlerNotFoundError, JobDefinitionNotFoundError
from domain.models.job import Job
from domain.ports.executor import ExecutionResult
from domain.ports.job_registry import JobRegistry

logger = logging.getLogger(__name__)


async def dispatch_job(
    job: Job,
    plugin_registry: JobRegistry,
    uow_factory: Callable[[], Any],
    prefer_db: bool = True,
) -> ExecutionResult:
    """
    Dispatch a job using hybrid registry and executor abstraction.
    
    This function:
    1. Creates DB registry from UoW session
    2. Composes hybrid registry (plugin + DB)
    3. Loads the job definition from hybrid registry
    4. Creates executor based on execution_mode
    5. Executes with timeout protection
    
    Args:
        job: The job to execute
        plugin_registry: Plugin-based registry (long-lived, in-memory)
        uow_factory: Factory for creating UnitOfWork instances
        prefer_db: If True, DB definitions override plugin ones
        
    Returns:
        ExecutionResult with success status and error if any
    """
    from adapters.outbound.executor.factory import create_executor
    from adapters.outbound.registry.job_registry_db import DbJobRegistry
    from adapters.outbound.registry.job_registry_hybrid import HybridJobRegistry
    
    handler: Callable
    timeout_s: int
    execution_mode: str
    
    # Create DB registry from UoW session and compose hybrid registry
    async with uow_factory() as uow:
        # Access the session from UoW
        db_registry = DbJobRegistry(uow._session)
        hybrid_registry = HybridJobRegistry(
            plugin_registry=plugin_registry,
            db_registry=db_registry,
            prefer_db=prefer_db,
        )

        # Get job definition from hybrid registry
        definition = await hybrid_registry.get_definition(job.name)
        if definition is None:
            raise JobDefinitionNotFoundError(
                f"Job definition '{job.name}' not found in registry"
            )
        logger.debug(
            "dispatch_job: resolved definition name=%s execution_mode=%s handler_ref=%s",
            definition.name,
            definition.execution_mode,
            definition.handler_ref,
        )

        # Store execution parameters
        timeout_s = definition.timeout_s
        execution_mode = definition.execution_mode
        required_capabilities = definition.capabilities

        # Resolve handler
        try:
            handler = await hybrid_registry.resolve_handler(definition.handler_ref)
        except HandlerNotFoundError as exc:
            logger.error(
                "Failed to resolve handler '%s' for job %s: %s",
                definition.handler_ref,
                job.id,
                exc,
            )
            raise

    # Log job execution details (outside UoW to avoid long transaction)
    logger.info(
        "Executing job %s (%s) with timeout=%ds, execution_mode=%s, capabilities=%s",
        job.id,
        job.name,
        timeout_s,
        execution_mode,
        required_capabilities,
    )

    # Create executor based on execution mode and execute
    executor = create_executor(execution_mode)
    
    return await executor.execute(
        handler=handler,
        payload=job.payload,
        timeout_s=timeout_s,
    )


def check_capabilities(
    required: list[str],
    available: set[str],
) -> bool:
    """
    Check if worker has all required capabilities.
    
    Args:
        required: List of required capabilities
        available: Set of available capabilities
        
    Returns:
        True if all required capabilities are available
    """
    if not required:
        return True  # No requirements = any worker can run
    
    return set(required).issubset(available)
