# adapters/outbound/executor/thread_pool_executor.py
"""
Thread pool executor - executes blocking/synchronous handlers in threads.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable

from domain.ports.executor import ExecutionResult, Executor

logger = logging.getLogger(__name__)


class ThreadPoolJobExecutor(Executor):
    """
    Executor for blocking/synchronous Python handlers.
    
    Runs handlers in a thread pool to avoid blocking the event loop.
    Useful for CPU-bound or blocking I/O operations.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize thread pool executor.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._max_workers = max_workers

    async def execute(
        self,
        handler: Callable,
        payload: dict[str, Any],
        timeout_s: int,
    ) -> ExecutionResult:
        """Execute blocking handler in thread pool with timeout."""
        loop = asyncio.get_event_loop()
        
        try:
            # Run in thread pool with timeout
            result = await asyncio.wait_for(
                loop.run_in_executor(self._executor, handler, payload),
                timeout=timeout_s,
            )
            return ExecutionResult(success=True, output=result)
        except asyncio.TimeoutError:
            logger.error(
                "Job execution exceeded timeout of %d seconds",
                timeout_s,
            )
            return ExecutionResult(
                success=False,
                error=TimeoutError(f"Job execution exceeded {timeout_s}s timeout"),
            )
        except Exception as exc:
            logger.exception("Job execution failed in thread pool")
            return ExecutionResult(success=False, error=exc)

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool executor."""
        self._executor.shutdown(wait=wait)

