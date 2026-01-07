from adapters.outbound.db import QueueOrm
from domain.models.queue import Queue


class QueueMapper:

    @staticmethod
    def to_domain(orm: QueueOrm) -> Queue:
        return Queue(
            name=orm.name,
            max_concurrency=orm.max_concurrency,
            active=orm.active,
        )
