from sqlalchemy import Column, UUID, String, Integer, Boolean

from adapters.outbound.db.base import Base


class QueueOrm(Base):

    __tablename__ = "queues"

    name = Column(String, primary_key=True)
    max_concurrency = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
