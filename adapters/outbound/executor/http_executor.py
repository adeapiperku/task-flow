# adapters/outbound/executor/http_executor.py
"""
HTTP executor - executes jobs by calling external webhooks/endpoints.
"""
import asyncio
import logging
from typing import Any, Callable

import httpx

from domain.ports.executor import ExecutionResult, Executor

logger = logging.getLogger(__name__)


class HttpExecutor(Executor):
    """
    Executor that executes jobs by calling HTTP endpoints.
    
    The handler should be a URL string, and payload is sent as JSON body.
    Useful for distributed job execution across services.
    """

    def __init__(self, timeout_s: int = 300, verify_ssl: bool = True):
        """
        Initialize HTTP executor.
        
        Args:
            timeout_s: Default timeout for HTTP requests
            verify_ssl: Whether to verify SSL certificates
        """
        self._default_timeout = timeout_s
        self._verify_ssl = verify_ssl

    async def execute(
        self,
        handler: Callable | str,
        payload: dict[str, Any],
        timeout_s: int,
    ) -> ExecutionResult:
        """
        Execute job by calling HTTP endpoint.
        
        Args:
            handler: URL string or callable that returns URL
            payload: Job payload (sent as JSON body)
            timeout_s: Request timeout
        """
        # If handler is a string, use it as URL
        # If it's callable, call it to get URL
        if callable(handler):
            url = handler()
        else:
            url = str(handler)

        if not url.startswith(("http://", "https://")):
            return ExecutionResult(
                success=False,
                error=ValueError(f"Invalid URL format: {url}"),
            )

        try:
            async with httpx.AsyncClient(
                timeout=timeout_s,
                verify=self._verify_ssl,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                
                result = response.json() if response.content else None
                return ExecutionResult(success=True, output=result)
                
        except httpx.TimeoutException:
            logger.error("HTTP request to %s timed out after %ds", url, timeout_s)
            return ExecutionResult(
                success=False,
                error=TimeoutError(f"HTTP request exceeded {timeout_s}s timeout"),
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP request to %s failed with status %d: %s",
                url,
                exc.response.status_code,
                exc.response.text,
            )
            return ExecutionResult(
                success=False,
                error=exc,
            )
        except Exception as exc:
            logger.exception("HTTP request to %s failed", url)
            return ExecutionResult(success=False, error=exc)

