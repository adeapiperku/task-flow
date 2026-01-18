# # adapters/outbound/db/models.py
# from __future__ import annotations

# import uuid
# from datetime import datetime

# from sqlalchemy import (
#     String,
#     DateTime,
#     Integer,
#     UUID as PG_UUID,
#     SmallInteger,
#     JSON,
#     Boolean,
#     Index,
#     Column,
#     TIMESTAMP,
#     func,
#     Text,
#     ForeignKey,
# )
# from sqlalchemy.dialects.postgresql import UUID, JSONB
# from sqlalchemy.orm import Mapped, mapped_column
# from sqlalchemy.orm import Mapped, mapped_column, relationship

# from adapters.outbound.db.base import Base
# from uuid import uuid4
# from sqlalchemy import (
#     Column,
#     String,
#     Integer,
#     Boolean,
#     DateTime,
#     Text,
#     ForeignKey,
# )
# from sqlalchemy.dialects.postgresql import UUID as PG_UUID
# from sqlalchemy.orm import relationship

# from adapters.outbound.db.base import Base

# class JobOrm(Base):
#     """
#     Low-level DB representation of a job.

#     This is NOT the rich domain model yet.
#     It is optimized for:
#       - scheduling queries
#       - audit / history
#       - multi-tenant queues
#     """
#     __tablename__ = "jobs"

#     # Primary key as UUID – good for distributed systems
#     id: Mapped[uuid.UUID] = mapped_column(
#         UUID(as_uuid=True),
#         primary_key=True,
#         default=uuid.uuid4,
#     )

#     # Logical queue name (e.g. "default", "gpu", "emails")
#     queue: Mapped[str] = mapped_column(
#         String(64),
#         default="default",
#         nullable=False,
#     )

#     # For debugging / observability (not necessarily unique)
#     name: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False,
#     )

#     # Tenant / project id for fairness and isolation
#     tenant_id: Mapped[str | None] = mapped_column(
#         String(64),
#         nullable=True,
#     )

#     # JSON payload the worker will receive
#     payload: Mapped[dict] = mapped_column(
#         JSONB,      # falls back to JSON if you ever change DB
#         nullable=False,
#     )

#     # Simple state machine for now – we can refine later
#     state: Mapped[str] = mapped_column(
#         String(32),  # PENDING, SCHEDULED, RUNNING, SUCCEEDED, FAILED, DEAD
#         nullable=False,
#         default="PENDING",
#     )

#     # Higher number ⇒ higher priority within a queue
#     priority: Mapped[int] = mapped_column(
#         SmallInteger,
#         nullable=False,
#         default=0,
#     )

#     # Scheduling timestamps
#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True),
#         default=datetime.utcnow,
#         nullable=False,
#     )
#     updated_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True),
#         default=datetime.utcnow,
#         onupdate=datetime.utcnow,
#         nullable=False,
#     )

#     # When it is/was supposed to run
#     scheduled_at: Mapped[datetime | None] = mapped_column(
#         DateTime(timezone=True),
#         nullable=True,
#     )
#     next_run_at: Mapped[datetime | None] = mapped_column(
#         DateTime(timezone=True),
#         nullable=True,
#         index=True,
#     )
#     last_run_at: Mapped[datetime | None] = mapped_column(
#         DateTime(timezone=True),
#         nullable=True,
#     )

#     # Retry logic
#     attempts: Mapped[int] = mapped_column(
#         Integer,
#         nullable=False,
#         default=0,
#     )
#     max_attempts: Mapped[int] = mapped_column(
#         Integer,
#         nullable=False,
#         default=3,
#     )

#     # Soft-delete / archival flag
#     archived: Mapped[bool] = mapped_column(
#         Boolean,
#         nullable=False,
#         default=False,
#     )

#     # Which worker currently owns it (for locks / heartbeats)
#     locked_by: Mapped[str | None] = mapped_column(
#         String(64),
#         nullable=True,
#     )
#     locked_at: Mapped[datetime | None] = mapped_column(
#         DateTime(timezone=True),
#         nullable=True,
#     )
#     lease_expires_at: Mapped[datetime | None] = mapped_column(
#         DateTime(timezone=True),
#         nullable=True,
#         index=True,  # Index for lease expiration queries
#     )

#     retry_strategy = Column(String(32), nullable=False, server_default="EXPONENTIAL")
#     retry_base_delay_seconds = Column(Integer, nullable=False, server_default="30")

# # Indexes that matter for scheduling performance:
# Index(
#     "ix_jobs_queue_state_priority_nextrun",
#     JobOrm.queue,
#     JobOrm.state,
#     JobOrm.priority.desc(),
#     JobOrm.next_run_at,
# )
# Index(
#     "ix_jobs_tenant_state",
#     JobOrm.tenant_id,
#     JobOrm.state,
# )

# class JobAttemptOrm(Base):
#     __tablename__ = "job_attempts"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     job_id = Column(
#         PG_UUID(as_uuid=True),
#         ForeignKey("jobs.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True,
#     )
#     attempt_number = Column(Integer, nullable=False)
#     started_at = Column(DateTime(timezone=True), nullable=False)
#     finished_at = Column(DateTime(timezone=True), nullable=False)
#     success = Column(Boolean, nullable=False)
#     error_type = Column(String(255), nullable=True)
#     error_message = Column(Text, nullable=True)
#     worker_id = Column(String(255), nullable=True)

#     job = relationship("JobOrm", backref="attempts_list")

# class JobDefinitionOrm(Base):
#     __tablename__ = "job_definitions"

#     name: Mapped[str] = mapped_column(Text, primary_key=True)

#     handler_ref: Mapped[str] = mapped_column(Text, nullable=False)
#     execution_mode: Mapped[str] = mapped_column(Text, nullable=False, default="python_async")

#     timeout_s: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
#     max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

#     backoff_policy: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
#     input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
#     resource_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
#     capabilities: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

#     visibility_timeout_s: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

#     version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

#     # created_at: Mapped = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
#     # updated_at: Mapped = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
#     created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
#     updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

# class AutomationRuleOrm(Base):
#     """ORM model for automation rules."""
#     __tablename__ = "automation_rules"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     name = Column(String(255), nullable=False)
#     description = Column(Text, nullable=True)
#     tenant_id = Column(String(255), nullable=False, index=True)
#     enabled = Column(Boolean, default=True, nullable=False)
#     trigger_type = Column(String(50), nullable=False)  # CRON, WEBHOOK, INTERNAL_EVENT
#     trigger_config = Column(JSONB, nullable=False)
#     created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, 
#                       onupdate=datetime.utcnow, nullable=False)
#     created_by = Column(String(255), nullable=False)
#     tags = Column(JSONB, default=dict, nullable=False)

#     # Relationships
#     conditions = relationship(
#         "AutomationRuleConditionOrm", 
#         back_populates="rule",
#         cascade="all, delete-orphan"
#     )
#     actions = relationship(
#         "AutomationRuleActionOrm", 
#         back_populates="rule",
#         cascade="all, delete-orphan"
#     )


# class AutomationRuleConditionOrm(Base):
#     """ORM model for automation rule conditions."""
#     __tablename__ = "automation_rule_conditions"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     rule_id = Column(
#         PG_UUID(as_uuid=True), 
#         ForeignKey("automation_rules.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )
#     field = Column(String(255), nullable=False)
#     operator = Column(String(50), nullable=False)  # eq, neq, gt, lt, contains, etc.
#     value = Column(JSONB, nullable=False)  # Store any JSON-serializable value

#     # Relationships
#     rule = relationship("AutomationRuleOrm", back_populates="conditions")

#     __table_args__ = (
#         Index('ix_automation_rule_conditions_rule_id', 'rule_id'),
#     )


# class AutomationRuleActionOrm(Base):
#     """ORM model for automation rule actions."""
#     __tablename__ = "automation_rule_actions"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     rule_id = Column(
#         PG_UUID(as_uuid=True),
#         ForeignKey("automation_rules.id", ondelete="CASCADE"),
#         nullable=False,
#         index=True
#     )
#     name = Column(String(255), nullable=False)
#     queue = Column(String(255), nullable=False)
#     payload = Column(JSONB, nullable=False)
#     tenant_id = Column(String(255), nullable=True, index=True)
#     priority = Column(Integer, default=0, nullable=False)
#     max_attempts = Column(Integer, default=3, nullable=False)

#     # Relationships
#     rule = relationship("AutomationRuleOrm", back_populates="actions")

#     __table_args__ = (
#         Index('ix_automation_rule_actions_rule_id', 'rule_id'),
#         Index('ix_automation_rule_actions_tenant_id', 'tenant_id'),
#     )
