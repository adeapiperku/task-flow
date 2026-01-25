"""Worker implementation with job processing and management."""
import asyncio
import logging
from typing import Callable, Optional, Set

from domain.models.job import Job
from domain.ports.job_registry import JobRegistry

from . import models as worker_models
from .exceptions import WorkerError, WorkerShutdownError
from .job_processor import JobProcessor
from .providers import WorkerProviders
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
        self._providers = WorkerProviders(
            uow_factory=uow_factory,
            plugin_registry=plugin_registry,
            prefer_db=self.config.prefer_db,
        )
        
        # Runtime state
        self._shutdown_event = asyncio.Event()
        self._running_tasks: Set[asyncio.Task] = set()
        self._semaphore = asyncio.Semaphore(self.config.concurrency)
        self.stats = worker_models.WorkerStats()
        self._processor = JobProcessor(
            config=self.config,
            providers=self._providers,
            stats=self.stats,
            semaphore=self._semaphore,
            shutdown_event=self._shutdown_event,
        )
    
    def _generate_worker_id(self) -> str:
        """Generate a unique worker ID."""
        from uuid import uuid4
        return str(uuid4())
    
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
            if not await self._processor.check_capabilities(job):
                continue

            # Start processing the job
            self._start_job_processing(job)
    
    async def _acquire_next_job(self) -> Optional[Job]:
        """Acquire the next job from the queue."""
        job = await self._providers.acquire_uc.execute(
            queue=self.config.queue,
            worker_id=self.config.worker_id,
        )
        if job:
            logger.debug("Worker %s acquired job %s", self.config.worker_id, job.id)
        return job
    
    def _start_job_processing(self, job: Job) -> None:
        """Start processing a job in a background task."""
        task = create_task_with_callback(
            self._processor.process(job),
            callback=self._running_tasks.discard,
            task_name=f"job-{job.id}",
        )
        self._running_tasks.add(task)
    
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
