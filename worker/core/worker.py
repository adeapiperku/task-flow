"""Worker implementation with job processing and management."""
import asyncio
import logging
import signal
from datetime import datetime
from typing import Callable, Optional, Set

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.outbound.registry.initializers import create_registry_from_handlers
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from application.use_cases.heartbeat_job import HeartbeatJobUseCase
from domain.models.job import Job
from domain.ports.job_registry import JobRegistry

from . import models as worker_models
from .dispatcher import check_capabilities, dispatch_job
from .exceptions import WorkerError, WorkerShutdownError
from .registry import RegistryManager
from .utils import create_task_with_callback, setup_signal_handlers

logger = logging.getLogger(__name__)


class Worker:
    """Production-ready worker with job processing and management."""

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
        """Initialize worker with configuration."""
        self.config = worker_models.WorkerConfig(
            queue=queue,
            worker_id=worker_id or f"worker-{self._generate_worker_id()}",
            poll_interval=poll_interval,
            prefer_db=prefer_db,
            capabilities=capabilities or set(),
            concurrency=concurrency,
            heartbeat_interval_s=heartbeat_interval_s,
        )
        
        # Initialize dependencies
        self._uow_factory = uow_factory or SqlAlchemyUnitOfWork
        self._plugin_registry = plugin_registry or self._create_default_registry()
        self._registry_manager = RegistryManager(
            plugin_registry=self._plugin_registry,
            uow_factory=self._uow_factory,
            prefer_db=self.config.prefer_db,
        )
        
        # Initialize use cases
        self._init_use_cases()
        
        # Runtime state
        self._shutdown_event = asyncio.Event()
        self._running_tasks: Set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        self.stats = worker_models.WorkerStats()
    
    def _generate_worker_id(self) -> str:
        """Generate a unique worker ID."""
        from uuid import uuid4
        return str(uuid4())
    
    def _create_default_registry(self) -> JobRegistry:
        """Create default registry from handlers."""
        from handlers import HANDLERS
        return create_registry_from_handlers(HANDLERS)
    
    def _init_use_cases(self):
        """Initialize use cases with dependencies."""
        self._acquire_uc = AcquireNextJobUseCase(uow_factory=self._uow_factory)
        self._complete_uc = CompleteJobUseCase(uow_factory=self._uow_factory)
        self._fail_uc = FailJobUseCase(uow_factory=self._uow_factory)
        self._heartbeat_uc = HeartbeatJobUseCase(uow_factory=self._uow_factory)
    
    async def run(self) -> None:
        """Run the worker main loop."""
        logger.info(
            "Worker %s started on queue '%s' with capabilities=%s, concurrency=%d",
            self.config.worker_id,
            self.config.queue,
            self.config.capabilities,
            self.config.concurrency,
        )

        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(self._shutdown_event)

        try:
            await self._run_loop()
        except asyncio.CancelledError:
            logger.info("Worker %s received cancellation signal", self.config.worker_id)
        except Exception as exc:
            logger.exception("Fatal error in worker %s", self.config.worker_id)
            raise WorkerError(f"Worker failed: {exc}") from exc
        finally:
            await self._shutdown()
    
    async def _run_loop(self) -> None:
        """Main worker processing loop."""
        while not self._shutdown_event.is_set():
            # Check if we have capacity
            if len(self._running_tasks) >= self.config.concurrency:
                await asyncio.sleep(self.config.poll_interval)
                continue

            # Try to acquire a job
            job = await self._acquire_next_job()
            if job is None:
                await asyncio.sleep(self.config.poll_interval)
                continue

            # Check capabilities
            if not await self._check_job_capabilities(job):
                continue

            # Start processing the job
            self._start_job_processing(job)
    
    async def _acquire_next_job(self) -> Optional[Job]:
        """Acquire the next job from the queue."""
        return await self._acquire_uc.execute(
            queue=self.config.queue,
            worker_id=self.config.worker_id,
        )
    
    async def _check_job_capabilities(self, job: Job) -> bool:
        """Check if worker has required capabilities for the job."""
        job_def = await self._registry_manager.get_job_definition(job.name)
        if job_def and not check_capabilities(
            required=job_def.capabilities,
            available=self.config.capabilities,
        ):
            logger.warning(
                "Worker %s rejected job %s: missing capabilities. "
                "Required: %s, Available: %s",
                self.config.worker_id,
                job.id,
                job_def.capabilities,
                self.config.capabilities,
            )
            self.stats.jobs_rejected += 1
            await self._fail_job_with_capability_error(job, job_def.capabilities)
            return False
        return True
    
    def _start_job_processing(self, job: Job) -> None:
        """Start processing a job in a background task."""
        task = create_task_with_callback(
            self._process_job_with_heartbeat(job),
            callback=self._running_tasks.discard,
            task_name=f"job-{job.id}",
        )
        self._running_tasks.add(task)
    
    async def _process_job_with_heartbeat(self, job: Job) -> None:
        """Process a job with periodic heartbeats."""
        async with self._semaphore:  # Concurrency control
            self.stats.jobs_processed += 1

            logger.info(
                "Worker %s processing job %s (%s, attempt %d/%d)",
                self.config.worker_id,
                job.id,
                job.name,
                job.attempts + 1,
                job.max_attempts,
            )

            started_at = datetime.utcnow()
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(job.id)
            )

            try:
                # Process the job
                result = await dispatch_job(
                    job=job,
                    plugin_registry=self._plugin_registry,
                    uow_factory=self._uow_factory,
                    prefer_db=self.config.prefer_db,
                )

                # Stop heartbeat
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

                # Handle job completion
                if result.success:
                    await self._handle_job_success(job, started_at)
                else:
                    await self._handle_job_failure(job, started_at, result.error)

            except Exception as exc:
                # Stop heartbeat on error
                if not heartbeat_task.done():
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                
                await self._handle_job_error(job, started_at, exc)
    
    async def _heartbeat_loop(self, job_id: str) -> None:
        """Send periodic heartbeats for a job."""
        try:
            while not self._shutdown_event.is_set():
                await asyncio.sleep(self.config.heartbeat_interval_s)
                await self._heartbeat_uc.execute(
                    job_id=job_id,
                    worker_id=self.config.worker_id,
                )
        except asyncio.CancelledError:
            logger.debug("Heartbeat task for job %s was cancelled", job_id)
            raise
        except Exception as exc:
            logger.error("Error in heartbeat loop for job %s: %s", job_id, exc)
    
    async def _handle_job_success(self, job: Job, started_at: datetime) -> None:
        """Handle successful job completion."""
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
            worker_id=self.config.worker_id,
        )

        self.stats.jobs_succeeded += 1
    
    async def _handle_job_failure(self, job: Job, started_at: datetime, error: Exception) -> None:
        """Handle job failure with an error."""
        finished_at = datetime.utcnow()
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
            worker_id=self.config.worker_id,
            error_type=error_type,
            error_message=error_message,
        )

        self.stats.jobs_failed += 1
    
    async def _handle_job_error(self, job: Job, started_at: datetime, exc: Exception) -> None:
        """Handle unexpected errors during job processing."""
        logger.exception("Unexpected error processing job %s", job.id)
        
        finished_at = datetime.utcnow()
        error_type = exc.__class__.__name__
        error_message = str(exc)

        await self._fail_uc.execute(
            job.id,
            started_at=started_at,
            finished_at=finished_at,
            worker_id=self.config.worker_id,
            error_type=error_type,
            error_message=error_message,
        )

        self.stats.jobs_failed += 1
    
    async def _fail_job_with_capability_error(
        self,
        job: Job,
        required_capabilities: list[str],
    ) -> None:
        """Fail a job due to missing capabilities."""
        error_msg = (
            f"Worker {self.config.worker_id} missing required capabilities. "
            f"Required: {required_capabilities}, Available: {self.config.capabilities}"
        )
        
        await self._fail_uc.execute(
            job_id=job.id,
            worker_id=self.config.worker_id,
            error_type="CapabilityError",
            error_message=error_msg,
        )
    
    async def _shutdown(self) -> None:
        """Perform graceful shutdown of the worker."""
        # Wait for running tasks to complete
        logger.info(
            "Worker %s shutting down, waiting for %d tasks...",
            self.config.worker_id,
            len(self._running_tasks),
        )
        
        if self._running_tasks:
            # Cancel all running tasks
            for task in self._running_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete or be cancelled
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
        
        # Log final statistics
        logger.info(
            "Worker %s stopped. Stats: processed=%d, succeeded=%d, failed=%d, rejected=%d, uptime=%.1fs",
            self.config.worker_id,
            self.stats.jobs_processed,
            self.stats.jobs_succeeded,
            self.stats.jobs_failed,
            self.stats.jobs_rejected,
            self.stats.uptime,
        )
