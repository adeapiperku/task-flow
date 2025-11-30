# adapters/outbound/db/models.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    SmallInteger,
    JSON,
    Boolean,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from adapters.outbound.db.base import Base


class JobOrm(Base):
    """
    Low-level DB representation of a job.

    This is NOT the rich domain model yet.
    It is optimized for:
      - scheduling queries
      - audit / history
      - multi-tenant queues
    """
    __tablename__ = "jobs"

    # Primary key as UUID – good for distributed systems
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Logical queue name (e.g. "default", "gpu", "emails")
    queue: Mapped[str] = mapped_column(
        String(64),
        default="default",
        nullable=False,
    )

    # For debugging / observability (not necessarily unique)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Tenant / project id for fairness and isolation
    tenant_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # JSON payload the worker will receive
    payload: Mapped[dict] = mapped_column(
        JSONB,      # falls back to JSON if you ever change DB
        nullable=False,
    )

    # Simple state machine for now – we can refine later
    state: Mapped[str] = mapped_column(
        String(32),  # PENDING, SCHEDULED, RUNNING, SUCCEEDED, FAILED, DEAD
        nullable=False,
        default="PENDING",
    )

    # Higher number ⇒ higher priority within a queue
    priority: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
    )

    # Scheduling timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # When it is/was supposed to run
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Retry logic
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    # Soft-delete / archival flag
    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Which worker currently owns it (for locks / heartbeats)
    locked_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


# Indexes that matter for scheduling performance:
Index(
    "ix_jobs_queue_state_priority_nextrun",
    JobOrm.queue,
    JobOrm.state,
    JobOrm.priority.desc(),
    JobOrm.next_run_at,
)
Index(
    "ix_jobs_tenant_state",
    JobOrm.tenant_id,
    JobOrm.state,
)
