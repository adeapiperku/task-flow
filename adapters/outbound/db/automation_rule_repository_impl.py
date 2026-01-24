# task_flow/adapters/outbound/db/automation_rule_repository_impl.py

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import json
from datetime import datetime

from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.automation_rule import (
    AutomationRule, Trigger, TriggerType, Condition, Action
)
from domain.ports.automation_rule_repository import AutomationRuleRepository
from adapters.outbound.db.models import (
    AutomationRuleOrm, AutomationRuleActionOrm, AutomationRuleConditionOrm
)


class SqlAlchemyAutomationRuleRepository(AutomationRuleRepository):
    """SQLAlchemy implementation of AutomationRuleRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def add(self, rule: AutomationRule) -> None:
        # Convert domain model to ORM model
        rule_dict = {
            'id': str(rule.id),
            'name': rule.name,
            'description': rule.description,
            'tenant_id': rule.tenant_id,
            'enabled': rule.enabled,
            'trigger_type': rule.trigger.type.value,
            'trigger_config': json.dumps(rule.trigger.config),
            'created_at': rule.created_at,
            'updated_at': rule.updated_at,
            'created_by': rule.created_by,
            'tags': json.dumps(rule.tags)
        }
        
        # Create rule
        rule_orm = AutomationRuleOrm(**rule_dict)
        self._session.add(rule_orm)
        
        # Add conditions
        for condition in rule.conditions:
            condition_orm = AutomationRuleConditionOrm(
                id=str(uuid4()),
                rule_id=rule.id,
                field=condition.field,
                operator=condition.operator,
                value=json.dumps(condition.value)
            )
            self._session.add(condition_orm)
        
        # Add actions
        for action in rule.actions:
            action_orm = AutomationRuleActionOrm(
                id=str(uuid4()),
                rule_id=rule.id,
                name=action.name,
                queue=action.queue,
                payload=json.dumps(action.payload),
                tenant_id=action.tenant_id,
                priority=action.priority,
                max_attempts=action.max_attempts
            )
            self._session.add(action_orm)
    
    async def get_by_id(self, rule_id: UUID, tenant_id: str) -> Optional[AutomationRule]:
        stmt = select(AutomationRuleOrm).where(
            and_(
                AutomationRuleOrm.id == str(rule_id),
                AutomationRuleOrm.tenant_id == tenant_id
            )
        )
        result = await self._session.execute(stmt)
        rule_orm = result.scalar_one_or_none()
        
        if not rule_orm:
            return None
            
        return await self._to_domain_model(rule_orm, self._session)
    
    async def list_by_tenant(
        self, 
        tenant_id: str, 
        enabled: Optional[bool] = None,
        trigger_type: Optional[str] = None
    ) -> List[AutomationRule]:
        stmt = select(AutomationRuleOrm).where(
            AutomationRuleOrm.tenant_id == tenant_id
        )
        
        if enabled is not None:
            stmt = stmt.where(AutomationRuleOrm.enabled == enabled)
            
        if trigger_type is not None:
            stmt = stmt.where(AutomationRuleOrm.trigger_type == trigger_type)
        
        result = await self._session.execute(stmt)
        rules_orm = result.scalars().all()
        
        return [
            await self._to_domain_model(rule_orm, self._session)
            for rule_orm in rules_orm
        ]
    
    async def update(self, rule: AutomationRule) -> None:
        # Update the rule
        stmt = (
            update(AutomationRuleOrm)
            .where(
                and_(
                    AutomationRuleOrm.id == str(rule.id),
                    AutomationRuleOrm.tenant_id == rule.tenant_id
                )
            )
            .values(
                name=rule.name,
                description=rule.description,
                enabled=rule.enabled,
                trigger_type=rule.trigger.type.value,
                trigger_config=json.dumps(rule.trigger.config),
                updated_at=datetime.utcnow(),
                tags=json.dumps(rule.tags)
            )
        )
        await self._session.execute(stmt)
        
        # Delete existing conditions and actions
        await self._session.execute(
            delete(AutomationRuleConditionOrm)
            .where(AutomationRuleConditionOrm.rule_id == str(rule.id))
        )
        
        await self._session.execute(
            delete(AutomationRuleActionOrm)
            .where(AutomationRuleActionOrm.rule_id == str(rule.id))
        )
        
        # Add updated conditions and actions
        for condition in rule.conditions:
            condition_orm = AutomationRuleConditionOrm(
                id=str(uuid4()),
                rule_id=rule.id,
                field=condition.field,
                operator=condition.operator,
                value=json.dumps(condition.value)
            )
            self._session.add(condition_orm)
        
        for action in rule.actions:
            action_orm = AutomationRuleActionOrm(
                id=str(uuid4()),
                rule_id=rule.id,
                name=action.name,
                queue=action.queue,
                payload=json.dumps(action.payload),
                tenant_id=action.tenant_id,
                priority=action.priority,
                max_attempts=action.max_attempts
            )
            self._session.add(action_orm)
    
    async def delete(self, rule_id: UUID, tenant_id: str) -> bool:
        # Delete conditions and actions first due to foreign key constraints
        await self._session.execute(
            delete(AutomationRuleConditionOrm)
            .where(AutomationRuleConditionOrm.rule_id == str(rule_id))
        )
        
        await self._session.execute(
            delete(AutomationRuleActionOrm)
            .where(AutomationRuleActionOrm.rule_id == str(rule_id))
        )
        
        # Delete the rule
        stmt = delete(AutomationRuleOrm).where(
            and_(
                AutomationRuleOrm.id == str(rule_id),
                AutomationRuleOrm.tenant_id == tenant_id
            )
        )
        result = await self._session.execute(stmt)
        
        return result.rowcount > 0
    
    async def _to_domain_model(
        self, 
        rule_orm: AutomationRuleOrm,
        session: AsyncSession
    ) -> AutomationRule:
        """Convert ORM model to domain model."""
        # Load conditions
        stmt = select(AutomationRuleConditionOrm).where(
            AutomationRuleConditionOrm.rule_id == rule_orm.id
        )
        result = await session.execute(stmt)
        conditions_orm = result.scalars().all()
        
        conditions = [
            Condition(
                field=cond.field,
                operator=cond.operator,
                value=json.loads(cond.value)
            )
            for cond in conditions_orm
        ]
        
        # Load actions
        stmt = select(AutomationRuleActionOrm).where(
            AutomationRuleActionOrm.rule_id == rule_orm.id
        )
        result = await session.execute(stmt)
        actions_orm = result.scalars().all()
        
        actions = [
            Action(
                name=action.name,
                queue=action.queue,
                payload=json.loads(action.payload),
                tenant_id=action.tenant_id,
                priority=action.priority,
                max_attempts=action.max_attempts
            )
            for action in actions_orm
        ]
        
        # Create domain model
        return AutomationRule(
            id=UUID(str(rule_orm.id)),
            name=rule_orm.name,
            description=rule_orm.description,
            tenant_id=rule_orm.tenant_id,
            enabled=rule_orm.enabled,
            trigger=Trigger(
                type=TriggerType(rule_orm.trigger_type),
                config=json.loads(rule_orm.trigger_config)
            ),
            conditions=conditions,
            actions=actions,
            created_at=rule_orm.created_at,
            updated_at=rule_orm.updated_at,
            created_by=rule_orm.created_by,
            tags=json.loads(rule_orm.tags) if rule_orm.tags else {}
        )
