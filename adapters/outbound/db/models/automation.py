# adapters/outbound/db/models/automation.py
from uuid import uuid4
from sqlalchemy import Column, UUID, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from adapters.outbound.db.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime

class AutomationRuleOrm(Base):
    """ORM model for automation rules."""
    __tablename__ = "automation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    trigger_type = Column(String(50), nullable=False)  # CRON, WEBHOOK, INTERNAL_EVENT
    trigger_config = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, 
                      onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)
    tags = Column(JSONB, default=dict, nullable=False)

    # Relationships
    conditions = relationship(
        "AutomationRuleConditionOrm", 
        back_populates="rule",
        cascade="all, delete-orphan"
    )
    actions = relationship(
        "AutomationRuleActionOrm", 
        back_populates="rule",
        cascade="all, delete-orphan"
    )


class AutomationRuleConditionOrm(Base):
    """ORM model for automation rule conditions."""
    __tablename__ = "automation_rule_conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id = Column(
        PG_UUID(as_uuid=True), 
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    field = Column(String(255), nullable=False)
    operator = Column(String(50), nullable=False)  # eq, neq, gt, lt, contains, etc.
    value = Column(JSONB, nullable=False)  # Store any JSON-serializable value

    # Relationships
    rule = relationship("AutomationRuleOrm", back_populates="conditions")

    __table_args__ = (
        Index('ix_automation_rule_conditions_rule_id', 'rule_id'),
    )


class AutomationRuleActionOrm(Base):
    """ORM model for automation rule actions."""
    __tablename__ = "automation_rule_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    queue = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=False)
    tenant_id = Column(String(255), nullable=True, index=True)
    priority = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Relationships
    rule = relationship("AutomationRuleOrm", back_populates="actions")

    __table_args__ = (
        Index('ix_automation_rule_actions_rule_id', 'rule_id'),
        Index('ix_automation_rule_actions_tenant_id', 'tenant_id'),
    )
