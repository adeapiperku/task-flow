# adapters/outbound/executor/python_async_executor.py
"""
Python async executor - executes async Python handlers.
"""
import asyncio
import logging
from typing import Any, Callable

from domain.ports.executor import ExecutionResult, Executor

logger = logging.getLogger(__name__)


class PythonAsyncExecutor(Executor):
    """
    Executor for async Python handlers.
    
    This is the default executor for most job types.
    Uses asyncio.wait_for for timeout protection.
    """

    async def execute(
        self,
        handler: Callable,
        payload: dict[str, Any],
        timeout_s: int,
    ) -> ExecutionResult:
        """Execute async Python handler with timeout."""
        try:
            result = await asyncio.wait_for(
                handler(payload),
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
            logger.exception("Job execution failed")
            return ExecutionResult(success=False, error=exc)

