from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Queue:
    """
    Domain model for a queue.
    """

    name: str
    max_concurrency: int
    priority: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def new(
        *,
        name: str,
        max_concurrency: int = 10,
        priority: int = 0,
    ) -> "Queue":
        now = datetime.utcnow()
        return Queue(
            name=name,
            max_concurrency=max_concurrency,
            priority=priority,
            created_at=now,
            updated_at=now,
        )

    def update_limits(
        self,
        *,
        max_concurrency: int | None = None,
        priority: int | None = None,
    ) -> "Queue":
        data: dict[str, Any] = self.__dict__.copy()
        if max_concurrency is not None:
            data["max_concurrency"] = max_concurrency
        if priority is not None:
            data["priority"] = priority
        data["updated_at"] = datetime.utcnow()
        return Queue(**data)
