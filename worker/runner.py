# worker/runner.py
"""
Production-ready worker implementation.

Features:
- Job registry integration (plugin + DB hybrid)
- Timeout handling based on job definitions
- Proper error handling and logging
- Graceful shutdown support
- Resource-aware execution
"""
import asyncio
import logging
import signal
from datetime import datetime
from typing import Callable, Optional
from uuid import uuid4

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.outbound.registry.initializers import create_registry_from_handlers
from adapters.outbound.registry.job_registry_db import DbJobRegistry
from adapters.outbound.registry.job_registry_hybrid import HybridJobRegistry
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from domain.exceptions import HandlerNotFoundError, JobDefinitionNotFoundError
from domain.models.job import Job
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


async def _execute_with_timeout(
    handler: Callable,
    payload: dict,
    timeout_s: int,
    job_id: str,
) -> None:
    """
    Execute a job handler with timeout protection.
    
    Args:
        handler: The handler function to execute
        payload: Job payload
        timeout_s: Timeout in seconds
        job_id: Job ID for logging
    """
    try:
        await asyncio.wait_for(
            handler(payload),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        logger.error(
            "Job %s exceeded timeout of %d seconds",
            job_id,
            timeout_s,
        )
        raise TimeoutError(f"Job execution exceeded {timeout_s}s timeout")


async def dispatch_job(
    job: Job,
    plugin_registry: JobRegistry,
    uow_factory: Callable[[], any],
    prefer_db: bool = True,
) -> None:
    """
    Dispatch a job using hybrid registry (plugin + DB).
    
    This function:
    1. Creates DB registry from UoW session
    2. Composes hybrid registry (plugin + DB)
    3. Loads the job definition from hybrid registry
    4. Resolves the handler
    5. Executes with timeout protection
    
    Args:
        job: The job to execute
        plugin_registry: Plugin-based registry (long-lived, in-memory)
        uow_factory: Factory for creating UnitOfWork instances
        prefer_db: If True, DB definitions override plugin ones
        
    Raises:
        JobDefinitionNotFoundError: If job definition not found
        HandlerNotFoundError: If handler cannot be resolved
        TimeoutError: If job execution exceeds timeout
        RuntimeError: For other execution errors
    """
    # Create DB registry from UoW session and compose hybrid registry
    # We do this inside UoW context to get the session, but execute handler outside
    # to avoid long-running transactions
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

        # Resolve handler (this is just importlib, doesn't need DB)
        # But we do it here to use the hybrid registry's resolution logic
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

        # Store execution parameters
        timeout_s = definition.timeout_s
        execution_mode = definition.execution_mode

    # Log job execution details (outside UoW to avoid long transaction)
    logger.info(
        "Executing job %s (%s) with timeout=%ds, execution_mode=%s",
        job.id,
        job.name,
        timeout_s,
        execution_mode,
    )

    # Execute handler outside UoW context to avoid long-running transaction
    await _execute_with_timeout(
        handler=handler,
        payload=job.payload,
        timeout_s=timeout_s,
        job_id=str(job.id),
    )


class Worker:
    """
    Production-ready worker that processes jobs from a queue.
    
    Features:
    - Job registry integration
    - Proper error handling
    - Metrics and logging
    - Graceful shutdown
    """

    def __init__(
        self,
        queue: str = "default",
        worker_id: Optional[str] = None,
        plugin_registry: Optional[JobRegistry] = None,
        uow_factory: Optional[Callable[[], any]] = None,
        poll_interval: float = 1.0,
        prefer_db: bool = True,
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
        """
        self.queue = queue
        self.worker_id = worker_id or f"worker-{uuid4()}"
        self.poll_interval = poll_interval
        self._uow_factory = uow_factory or SqlAlchemyUnitOfWork
        self._prefer_db = prefer_db
        
        # Initialize plugin registry (long-lived, in-memory)
        # In production, this could be loaded from installed packages via entrypoints
        if plugin_registry is None:
            self._plugin_registry = create_registry_from_handlers(HANDLERS)
        else:
            self._plugin_registry = plugin_registry

        # Initialize use cases
        self._acquire_uc = AcquireNextJobUseCase(uow_factory=self._uow_factory)
        self._complete_uc = CompleteJobUseCase(uow_factory=self._uow_factory)
        self._fail_uc = FailJobUseCase(uow_factory=self._uow_factory)

        # Statistics
        self._jobs_processed = 0
        self._jobs_succeeded = 0
        self._jobs_failed = 0

    async def run(self) -> None:
        """Run the worker loop."""
        logger.info(
            "Worker %s started on queue '%s'",
            self.worker_id,
            self.queue,
        )

        _setup_signal_handlers()

        try:
            while not _shutdown_requested:
                job = await self._acquire_uc.execute(
                    queue=self.queue,
                    worker_id=self.worker_id,
                )

                if job is None:
                    # No jobs available, wait before polling again
                    await asyncio.sleep(self.poll_interval)
                    continue

                await self._process_job(job)

        except KeyboardInterrupt:
            logger.info("Worker %s interrupted", self.worker_id)
        except Exception as exc:
            logger.exception("Fatal error in worker %s", self.worker_id)
            raise
        finally:
            logger.info(
                "Worker %s shutting down. Stats: processed=%d, succeeded=%d, failed=%d",
                self.worker_id,
                self._jobs_processed,
                self._jobs_succeeded,
                self._jobs_failed,
            )

    async def _process_job(self, job: Job) -> None:
        """
        Process a single job.
        
        Handles:
        - Job execution with timeout
        - Success/failure recording
        - Error handling and logging
        """
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

        try:
            await dispatch_job(
                job=job,
                plugin_registry=self._plugin_registry,
                uow_factory=self._uow_factory,
                prefer_db=self._prefer_db,
            )

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

        except (JobDefinitionNotFoundError, HandlerNotFoundError) as exc:
            # These are configuration errors, mark job as failed
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
            # Runtime error during job execution
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


async def worker_loop(queue: str = "default") -> None:
    """
    Convenience function to run a worker.
    
    This is the entry point for simple deployments.
    For more control, use the Worker class directly.
    
    Args:
        queue: Queue name to process
    """
    worker = Worker(queue=queue)
    await worker.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(worker_loop())
