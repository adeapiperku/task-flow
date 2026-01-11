# adapters/outbound/executor/factory.py
"""
Factory for creating executor instances based on execution mode.
"""
from __future__ import annotations

from adapters.outbound.executor.http_executor import HttpExecutor
from adapters.outbound.executor.python_async_executor import PythonAsyncExecutor
from adapters.outbound.executor.thread_pool_executor import ThreadPoolJobExecutor
from domain.ports.executor import Executor


def create_executor(execution_mode: str, **kwargs) -> Executor:
    """
    Create an executor based on execution mode.
    
    Args:
        execution_mode: Execution mode string (python_async, thread_pool, http, etc.)
        **kwargs: Additional arguments for executor initialization
        
    Returns:
        Executor instance
        
    Raises:
        ValueError: If execution_mode is not supported
    """
    if execution_mode == "python_async":
        return PythonAsyncExecutor()
    elif execution_mode == "thread_pool":
        max_workers = kwargs.get("max_workers", 4)
        return ThreadPoolJobExecutor(max_workers=max_workers)
    elif execution_mode == "http":
        timeout_s = kwargs.get("timeout_s", 300)
        verify_ssl = kwargs.get("verify_ssl", True)
        return HttpExecutor(timeout_s=timeout_s, verify_ssl=verify_ssl)
    else:
        raise ValueError(f"Unsupported execution mode: {execution_mode}")

