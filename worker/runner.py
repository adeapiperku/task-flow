# worker/runner.py
"""
Production-ready worker implementation with:
- Executor abstraction (python_async, thread_pool, http)
- Capability-based job routing
- Lease management with heartbeats
- Concurrency control and backpressure
"""
import asyncio
import logging
import signal
from datetime import datetime
from typing import Callable, Optional, Set
from uuid import uuid4

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.outbound.executor.factory import create_executor
from adapters.outbound.registry.initializers import create_registry_from_handlers
from adapters.outbound.registry.job_registry_db import DbJobRegistry
from adapters.outbound.registry.job_registry_hybrid import HybridJobRegistry
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from application.use_cases.heartbeat_job import HeartbeatJobUseCase
from domain.exceptions import HandlerNotFoundError, JobDefinitionNotFoundError
from domain.models.job import Job
from domain.ports.executor import ExecutionResult
from domain.ports.job_registry import JobRegistry
from handlers import HANDLERS

logger = logging.getLogger(__name__)

# Global shutdown flag for graceful shutdown
_shutdown_requested = False


def _setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    global _shutdown_requested

    def signal_handler(signum, frame):
        logger.info("Received shutdown signal %s", signum)
        _shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def dispatch_job(
    job: Job,
    plugin_registry: JobRegistry,
    uow_factory: Callable[[], any],
    prefer_db: bool = True,
) -> ExecutionResult:
    """
    Dispatch a job using hybrid registry and executor abstraction.
    
    This function:
    1. Creates DB registry from UoW session
    2. Composes hybrid registry (plugin + DB)
    3. Loads the job definition from hybrid registry
    4. Checks worker capabilities
    5. Resolves the handler
    6. Creates executor based on execution_mode
    7. Executes with timeout protection
    
    Args:
        job: The job to execute
        plugin_registry: Plugin-based registry (long-lived, in-memory)
        uow_factory: Factory for creating UnitOfWork instances
        prefer_db: If True, DB definitions override plugin ones
        
    Returns:
        ExecutionResult with success status and error if any
    """
    handler: Callable
    timeout_s: int
    execution_mode: str
    required_capabilities: list[str]
    
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

    # Create executor based on execution mode
    executor = create_executor(execution_mode)
    
    # Execute using executor
    result = await executor.execute(
        handler=handler,
        payload=job.payload,
        timeout_s=timeout_s,
    )
    
    return result


def check_capabilities(
    required: list[str],
    available: Set[str],
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


class Worker:
    """
    Production-ready worker with executor abstraction, capability routing,
    lease management, and concurrency control.
    """

    def __init__(
        self,
        queue: str = "default",
        worker_id: Optional[str] = None,
        plugin_registry: Optional[JobRegistry] = None,
        uow_factory: Optional[Callable[[], any]] = None,
        poll_interval: float = 1.0,
        prefer_db: bool = True,
        capabilities: Optional[Set[str]] = None,
        concurrency: int = 4,
        heartbeat_interval_s: float = 30.0,
    ):
        """
        Initialize worker.
        
        Args:
            queue: Queue name to process
            worker_id: Optional worker ID (auto-generated if not provided)
            plugin_registry: Optional plugin registry (uses default from HANDLERS if not provided)
            uow_factory: Optional UoW factory (uses SqlAlchemyUnitOfWork if not provided)
            poll_interval: Seconds to wait when no jobs available
            prefer_db: If True, DB definitions override plugin ones (default: True)
            capabilities: Set of worker capabilities (e.g., {"network", "cpu", "gpu"})
            concurrency: Maximum number of concurrent jobs
            heartbeat_interval_s: Interval between heartbeats in seconds
        """
        self.queue = queue
        self.worker_id = worker_id or f"worker-{uuid4()}"
        self.poll_interval = poll_interval
        self._uow_factory = uow_factory or SqlAlchemyUnitOfWork
        self._prefer_db = prefer_db
        self._capabilities = capabilities or set()
        self._concurrency = concurrency
        self._heartbeat_interval_s = heartbeat_interval_s
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running_tasks: Set[asyncio.Task] = set()
        
        # Initialize plugin registry (long-lived, in-memory)
        if plugin_registry is None:
            self._plugin_registry = create_registry_from_handlers(HANDLERS)
        else:
            self._plugin_registry = plugin_registry

        # Initialize use cases
        self._acquire_uc = AcquireNextJobUseCase(uow_factory=self._uow_factory)
        self._complete_uc = CompleteJobUseCase(uow_factory=self._uow_factory)
        self._fail_uc = FailJobUseCase(uow_factory=self._uow_factory)
        self._heartbeat_uc = HeartbeatJobUseCase(uow_factory=self._uow_factory)

        # Statistics
        self._jobs_processed = 0
        self._jobs_succeeded = 0
        self._jobs_failed = 0
        self._jobs_rejected_capabilities = 0

    async def run(self) -> None:
        """Run the worker loop."""
        logger.info(
            "Worker %s started on queue '%s' with capabilities=%s, concurrency=%d",
            self.worker_id,
            self.queue,
            self._capabilities,
            self._concurrency,
        )

        _setup_signal_handlers()

        try:
            while not _shutdown_requested:
                # Check if we have capacity
                if len(self._running_tasks) >= self._concurrency:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Try to acquire a job
                job = await self._acquire_uc.execute(
                    queue=self.queue,
                    worker_id=self.worker_id,
                )

                if job is None:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Check capabilities
                job_def = await self._get_job_definition(job.name)
                if job_def and not check_capabilities(
                    required=job_def.capabilities,
                    available=self._capabilities,
                ):
                    logger.warning(
                        "Worker %s rejected job %s: missing capabilities. "
                        "Required: %s, Available: %s",
                        self.worker_id,
                        job.id,
                        job_def.capabilities,
                        self._capabilities,
                    )
                    self._jobs_rejected_capabilities += 1
                    # TODO: Requeue to different queue or fail
                    await self._fail_job_with_capability_error(job, job_def.capabilities)
                    continue

                # Spawn task for job processing
                task = asyncio.create_task(
                    self._process_job_with_heartbeat(job)
                )
                self._running_tasks.add(task)
                task.add_done_callback(self._running_tasks.discard)

        except KeyboardInterrupt:
            logger.info("Worker %s interrupted", self.worker_id)
        except Exception as exc:
            logger.exception("Fatal error in worker %s", self.worker_id)
            raise
        finally:
            # Wait for running tasks to complete
            logger.info(
                "Worker %s shutting down, waiting for %d tasks...",
                self.worker_id,
                len(self._running_tasks),
            )
            if self._running_tasks:
                await asyncio.gather(*self._running_tasks, return_exceptions=True)
            
            logger.info(
                "Worker %s stopped. Stats: processed=%d, succeeded=%d, failed=%d, rejected=%d",
                self.worker_id,
                self._jobs_processed,
                self._jobs_succeeded,
                self._jobs_failed,
                self._jobs_rejected_capabilities,
            )

    async def _get_job_definition(self, job_name: str):
        """Get job definition from registry."""
        async with self._uow_factory() as uow:
            db_registry = DbJobRegistry(uow._session)
            hybrid_registry = HybridJobRegistry(
                plugin_registry=self._plugin_registry,
                db_registry=db_registry,
                prefer_db=self._prefer_db,
            )
            return await hybrid_registry.get_definition(job_name)

    async def _process_job_with_heartbeat(self, job: Job) -> None:
        """
        Process a job with periodic heartbeats to extend the lease.
        """
        async with self._semaphore:  # Concurrency control
            self._jobs_processed += 1

            logger.info(
                "Worker %s processing job %s (%s, attempt %d/%d)",
                self.worker_id,
                job.id,
                job.name,
                job.attempts + 1,
                job.max_attempts,
            )

            started_at = datetime.utcnow()
            error_type: Optional[str] = None
            error_message: Optional[str] = None

            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(job.id)
            )

            try:
                # Dispatch job using executor abstraction
                result = await dispatch_job(
                    job=job,
                    plugin_registry=self._plugin_registry,
                    uow_factory=self._uow_factory,
                    prefer_db=self._prefer_db,
                )

                # Stop heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                if result.success:
                    # Job succeeded
                    finished_at = datetime.utcnow()
                    execution_time = (finished_at - started_at).total_seconds()

                    logger.info(
                        "Job %s completed successfully in %.2fs",
                        job.id,
                        execution_time,
                    )

                    await self._complete_uc.execute(
                        job.id,
                        started_at=started_at,
                        finished_at=finished_at,
                        worker_id=self.worker_id,
                    )

                    self._jobs_succeeded += 1
                else:
                    # Job failed
                    finished_at = datetime.utcnow()
                    error = result.error
                    error_type = error.__class__.__name__ if error else "UnknownError"
                    error_message = str(error) if error else "Execution failed"

                    logger.error(
                        "Job %s failed: %s",
                        job.id,
                        error_message,
                    )

                    await self._fail_uc.execute(
                        job.id,
                        started_at=started_at,
                        finished_at=finished_at,
                        worker_id=self.worker_id,
                        error_type=error_type,
                        error_message=error_message,
                    )

                    self._jobs_failed += 1

            except (JobDefinitionNotFoundError, HandlerNotFoundError) as exc:
                # Stop heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                finished_at = datetime.utcnow()
                error_type = exc.__class__.__name__
                error_message = str(exc)

                logger.error(
                    "Job %s failed due to configuration error: %s",
                    job.id,
                    error_message,
                )

                await self._fail_uc.execute(
                    job.id,
                    started_at=started_at,
                    finished_at=finished_at,
                    worker_id=self.worker_id,
                    error_type=error_type,
                    error_message=error_message,
                )

                self._jobs_failed += 1

            except Exception as exc:
                # Stop heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                finished_at = datetime.utcnow()
                error_type = exc.__class__.__name__
                error_message = str(exc)

                logger.exception(
                    "Job %s failed with error: %s",
                    job.id,
                    error_message,
                )

                await self._fail_uc.execute(
                    job.id,
                    started_at=started_at,
                    finished_at=finished_at,
                    worker_id=self.worker_id,
                    error_type=error_type,
                    error_message=error_message,
                )

                self._jobs_failed += 1

    async def _heartbeat_loop(self, job_id) -> None:
        """
        Periodically send heartbeats to extend the lease.
        
        This prevents the job from being reclaimed if processing takes longer
        than the initial visibility timeout.
        """
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval_s)
                
                try:
                    # Get visibility timeout from job definition
                    # For now, use default 300s - could be improved to get from definition
                    await self._heartbeat_uc.execute(
                        job_id=job_id,
                        visibility_timeout_s=300,
                    )
                    logger.debug("Heartbeat sent for job %s", job_id)
                except Exception as exc:
                    logger.warning(
                        "Failed to send heartbeat for job %s: %s",
                        job_id,
                        exc,
                    )
                    # Continue trying - job might complete soon
        except asyncio.CancelledError:
            logger.debug("Heartbeat loop cancelled for job %s", job_id)
            raise

    async def _fail_job_with_capability_error(
        self,
        job: Job,
        required_capabilities: list[str],
    ) -> None:
        """Fail a job due to missing capabilities."""
        await self._fail_uc.execute(
            job.id,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            worker_id=self.worker_id,
            error_type="CapabilityError",
            error_message=f"Worker missing required capabilities: {required_capabilities}",
        )


async def worker_loop(
    queue: str = "default",
    capabilities: Optional[Set[str]] = None,
    concurrency: int = 4,
) -> None:
    """
    Convenience function to run a worker.
    
    Args:
        queue: Queue name to process
        capabilities: Set of worker capabilities
        concurrency: Maximum concurrent jobs
    """
    worker = Worker(
        queue=queue,
        capabilities=capabilities,
        concurrency=concurrency,
    )
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(worker_loop())
