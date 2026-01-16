# domain/models/automation_rule.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from domain.models.job import Job


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

    @staticmethod
    def create(
        name: str,
        description: str,
        tenant_id: str,
        trigger: Trigger,
        actions: List[Action],
        created_by: str,
        conditions: Optional[List[Condition]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> 'AutomationRule':
        """Factory method to create a new AutomationRule."""
        now = datetime.utcnow()
        return AutomationRule(
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
        """Evaluate a single condition."""
        try:
            if condition.operator == 'eq':
                return value == condition.value
            elif condition.operator == 'neq':
                return value != condition.value
            elif condition.operator == 'gt':
                return value > condition.value
            elif condition.operator == 'lt':
                return value < condition.value
            elif condition.operator == 'contains':
                return condition.value in value
            # Add more operators as needed
            return False
        except (TypeError, AttributeError):
            return False

    def generate_jobs(self) -> List[Job]:
        """
        Generate Job instances based on the rule's actions.
        This should be called after conditions are evaluated and passed.
        """
        from domain.models.job import Job, JobState
        from domain.models.retry_policy import RetryPolicy

        now = datetime.utcnow()
        jobs = []

        for action in self.actions:
            job = Job(
                id=uuid4(),
                queue=action.queue,
                name=action.name,
                payload=action.payload,
                tenant_id=action.tenant_id or self.tenant_id,
                state=JobState.PENDING,
                priority=action.priority,
                created_at=now,
                updated_at=now,
                scheduled_at=now,
                next_run_at=now,
                last_run_at=None,
                attempts=0,
                max_attempts=action.max_attempts,
                archived=False,
                locked_by=None,
                locked_at=None,
                retry_policy=RetryPolicy(
                    max_retries=action.max_attempts - 1,
                    initial_delay_seconds=30,
                    max_delay_seconds=3600,
                    backoff_factor=2,
                    jitter=True
                )
            )
            jobs.append(job)

        return jobs

