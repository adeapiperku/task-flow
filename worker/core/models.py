"""Data models and types for the worker."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


@dataclass
class WorkerStats:
    """Statistics about worker performance."""
    jobs_processed: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    jobs_rejected: int = 0
    start_time: datetime = field(default_factory=datetime.utcnow)

    @property
    def uptime(self) -> float:
        """Return worker uptime in seconds."""
        return (datetime.utcnow() - self.start_time).total_seconds()


@dataclass
class WorkerConfig:
    """Configuration for the worker."""
    queue: str = "default"
    worker_id: str = ""
    poll_interval: float = 1.0
    prefer_db: bool = True
    capabilities: Set[str] = field(default_factory=set)
    concurrency: int = 4
    heartbeat_interval_s: float = 30.0
