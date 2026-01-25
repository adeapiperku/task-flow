from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from adapters.outbound.db.base import Base

class TenantOrm(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    max_running_jobs = Column(Integer, nullable=False, server_default="5")
    active = Column(Boolean, nullable=False, server_default="true")
