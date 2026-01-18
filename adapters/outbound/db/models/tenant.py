from sqlalchemy import Column, UUID, String, Integer, Boolean

from adapters.outbound.db.base import Base

class TenantOrm(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    max_running_jobs = Column(Integer, nullable=False, default=5)
    active = Column(Boolean, default=True)
