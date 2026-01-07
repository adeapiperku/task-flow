from typing import Protocol
from domain.models.queue import Queue


class QueueRepository(Protocol):
    async def get_by_name(self, name: str) -> Queue | None: ...
    async def save(self, queue: Queue) -> None: ...
