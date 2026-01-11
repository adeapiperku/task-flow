# domain/ports/executor.py
from __future__ import annotations

from typing import Any, Callable, Protocol


class ExecutionResult:
    """Result of job execution."""
    
    def __init__(
        self,
        success: bool,
        error: Exception | None = None,
        output: Any = None,
    ):
        self.success = success
        self.error = error
        self.output = output


class Executor(Protocol):
    """
    Port for executing jobs with different strategies.
    
    The domain layer depends on this protocol, not on concrete execution implementations.
    This allows jobs to run in different environments: async Python, threads, processes,
    containers, HTTP webhooks, Kubernetes, etc.
    """

    async def execute(
        self,
        handler: Callable,
        payload: dict[str, Any],
        timeout_s: int,
    ) -> ExecutionResult:
        """
        Execute a job handler with the given payload and timeout.
        
        Args:
            handler: The handler function to execute
            payload: Job payload
            timeout_s: Maximum execution time in seconds
            
        Returns:
            ExecutionResult with success status and optional error/output
        """
        ...

