# domain/models/automation_rule.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from domain.models.job import Job
from domain.validators import (
    evaluate_condition,
    validate_not_empty,
    validate_in_enum,
    ConditionOperator, ValidationError
)


class TriggerType(str, Enum):
    CRON = "CRON"
    WEBHOOK = "WEBHOOK"
    INTERNAL_EVENT = "INTERNAL_EVENT"


@dataclass(frozen=True)
class Trigger:
    type: TriggerType
    config: Dict[str, Any]


@dataclass(frozen=True)
class Condition:
    field: str
    operator: str  # 'eq', 'neq', 'gt', 'lt', 'contains', etc.
    value: Any


@dataclass(frozen=True)
class Action:
    name: str
    queue: str
    payload: Dict[str, Any]
    tenant_id: Optional[str] = None
    priority: int = 0
    max_attempts: int = 3


@dataclass(frozen=True)
class AutomationRule:
    """
    Represents a rule that can trigger job creation based on certain conditions.
    """
    id: UUID
    name: str
    description: str
    tenant_id: str
    enabled: bool
    trigger: Trigger
    conditions: List[Condition]
    actions: List[Action]
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        tenant_id: str,
        trigger: Trigger,
        actions: List[Action],
        created_by: str,
        conditions: Optional[List[Condition]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> 'AutomationRule':
        """
        Factory method to create a new AutomationRule with validation.
        
        Args:
            name: Name of the rule
            description: Description of the rule
            tenant_id: ID of the tenant this rule belongs to
            trigger: The trigger configuration
            actions: List of actions to execute when the rule is triggered
            created_by: ID of the user creating the rule
            conditions: Optional list of conditions that must be met
            tags: Optional key-value pairs for categorization
            
        Returns:
            A new AutomationRule instance
            
        Raises:
            ValidationError: If any validation fails
        """
        # Validate required fields
        validate_not_empty(name, "name")
        validate_not_empty(tenant_id, "tenant_id")
        validate_not_empty(created_by, "created_by")
        
        if not actions:
            raise ValidationError(
                "At least one action is required",
                field="actions",
                code="missing_actions"
            )
            
        # Validate trigger type
        validate_in_enum(trigger.type, TriggerType, "trigger.type")
        
        now = datetime.utcnow()
        return cls(
            id=uuid4(),
            name=name,
            description=description,
            tenant_id=tenant_id,
            enabled=True,
            trigger=trigger,
            conditions=conditions or [],
            actions=actions,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            tags=tags or {},
        )

    def evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions against the provided context.
        Returns True only if all conditions are met.
        """
        if not self.conditions:
            return True

        for condition in self.conditions:
            value = context.get(condition.field)
            if not self._evaluate_condition(condition, value):
                return False
        return True

    def _evaluate_condition(self, condition: Condition, value: Any) -> bool:
        """Evaluate a single condition using the centralized validator."""
        try:
            return evaluate_condition(
                field=condition.field,
                operator=condition.operator,
                expected_value=condition.value,
                context={condition.field: value}
            )
        except ValueError:
            # Log warning about unsupported operator
            import logging
            logging.warning(f"Unsupported operator in condition: {condition.operator}")
            return False

    def generate_jobs(self) -> List[Job]:
        """
        Generate Job instances based on the rule's actions.
        This should be called after conditions are evaluated and passed.
        """
        from domain.models.job import Job

        now = datetime.utcnow()
        jobs = []

        for action in self.actions:
            job = Job.new(
                name=action.name,
                payload=action.payload,
                queue=action.queue,
                tenant_id=action.tenant_id or self.tenant_id,
                priority=action.priority,
                max_attempts=action.max_attempts,
                scheduled_at=now,
            )
            jobs.append(job)

        return jobs

