"""Utility functions for the worker."""
import asyncio
import logging
import signal
from typing import Any, Callable, Coroutine, Optional, TypeVar

from worker.core.exceptions import WorkerShutdownError

T = TypeVar('T')

__all__ = [
    'run_with_timeout',
    'setup_signal_handlers',
    'create_task_with_callback'
]

async def run_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    task_name: str = "task"
) -> T:
    """Run a coroutine with a timeout.
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        task_name: Name of the task for logging
        
    Returns:
        The result of the coroutine
        
    Raises:
        asyncio.TimeoutError: If the coroutine takes longer than timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logging.error("%s timed out after %.2f seconds", task_name, timeout)
        raise

def setup_signal_handlers(shutdown_event: asyncio.Event):
    """Setup signal handlers for graceful shutdown.
    
    Args:
        shutdown_event: Event to set when shutdown is requested
    """
    def signal_handler(signum, frame):
        logging.info("Received signal %s, shutting down...", signum)
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def create_task_with_callback(
    coro: Coroutine[Any, Any, T],
    callback: Optional[Callable[[asyncio.Task[T]], None]] = None,
    task_name: Optional[str] = None
) -> asyncio.Task[T]:
    """Create a task with an optional callback when done.
    
    Args:
        coro: Coroutine to run as a task
        callback: Optional callback to call when task is done
        task_name: Optional name for the task
        
    Returns:
        The created task
    """
    task = asyncio.create_task(coro)
    if task_name:
        task.set_name(task_name)
    
    if callback is not None:
        task.add_done_callback(callback)
    
    return task
