# domain/ports/event_bus.py
from __future__ import annotations

from typing import Protocol

from domain.models.job import Job


class EventBus(Protocol):
    """
    Port for publishing domain events.
    
    The domain layer depends on this protocol, not on any concrete broker implementation.
    This allows the system to publish events without coupling to Redis, RabbitMQ, etc.
    """

    async def publish_job_created(self, job: Job) -> None:
        """
        Publish an event when a job is created/scheduled.
        
        Args:
            job: The newly created job
        """
        ...

    async def publish_job_started(self, job: Job, worker_id: str) -> None:
        """
        Publish an event when a job starts execution.
        
        Args:
            job: The job that started
            worker_id: ID of the worker executing the job
        """
        ...

    async def publish_job_completed(self, job: Job, execution_time_ms: int | None = None) -> None:
        """
        Publish an event when a job completes successfully.
        
        Args:
            job: The completed job
            execution_time_ms: Optional execution time in milliseconds
        """
        ...

    async def publish_job_failed(self, job: Job, error_message: str | None = None) -> None:
        """
        Publish an event when a job fails.
        
        Args:
            job: The failed job
            error_message: Optional error message
        """
        ...

    async def publish_job_dead(self, job: Job, error_message: str | None = None) -> None:
        """
        Publish an event when a job is marked as DEAD (max attempts exhausted).
        
        Args:
            job: The dead job
            error_message: Optional error message
        """
        ...

    async def publish_job_retry_scheduled(self, job: Job, next_run_at: str) -> None:
        """
        Publish an event when a job is scheduled for retry.
        
        Args:
            job: The job being retried
            next_run_at: ISO format timestamp of next run
        """
        ...


