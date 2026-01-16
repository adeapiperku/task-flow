# adapters/inbound/api/routers/automation_rules.py

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from domain.models.automation_rule import (
    AutomationRule, Trigger, TriggerType, Condition, Action
)
from domain.ports.automation_rule_repository import AutomationRuleRepository
from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.outbound.db.models import (
    AutomationRuleOrm, 
    AutomationRuleConditionOrm, 
    AutomationRuleActionOrm
)

router = APIRouter(prefix="/automation-rules", tags=["automation"])

# Request/Response Models
class TriggerSchema(BaseModel):
    type: str
    config: Dict[str, Any]

class ConditionSchema(BaseModel):
    field: str
    operator: str
    value: Any

class ActionSchema(BaseModel):
    name: str
    queue: str
    payload: Dict[str, Any]
    tenant_id: Optional[str] = None
    priority: int = 0
    max_attempts: int = 3

class AutomationRuleBase(BaseModel):
    name: str
    description: str
    enabled: bool = True
    trigger: TriggerSchema
    conditions: List[ConditionSchema] = []
    actions: List[ActionSchema]
    tags: Dict[str, str] = {}

class AutomationRuleCreate(AutomationRuleBase):
    pass

class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    trigger: Optional[TriggerSchema] = None
    conditions: Optional[List[ConditionSchema]] = None
    actions: Optional[List[ActionSchema]] = None
    tags: Optional[Dict[str, str]] = None

class AutomationRuleResponse(AutomationRuleBase):
    id: UUID
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True

# Dependencies
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_uow() -> SqlAlchemyUnitOfWork:
    uow = SqlAlchemyUnitOfWork()
    await uow.__aenter__()
    return uow

async def get_automation_rule_repository(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow)
) -> AutomationRuleRepository:
    return uow.automation_rules

# @asynccontextmanager
# async def get_automation_rule_repository():
#     uow = SqlAlchemyUnitOfWork()
#     try:
#         async with uow:
#             yield uow.automation_rules
#     finally:
#         await uow.__aexit__(None, None, None)

# API Endpoints
# @router.post("", response_model=AutomationRuleResponse, status_code=201)
# async def create_rule(
#     rule_data: AutomationRuleCreate,
#     tenant_id: str = "default-tenant",
#     created_by: str = "system",
#     repo: AutomationRuleRepository = Depends(get_automation_rule_repository),
# ):
@router.post("", response_model=AutomationRuleResponse, status_code=201)
async def create_rule(
    rule_data: AutomationRuleCreate,
    tenant_id: str = "default-tenant",
    created_by: str = "system",
    repo: AutomationRuleRepository = Depends(get_automation_rule_repository),
):

    # Create a new automation rule.
    # Convert to domain model
    trigger = Trigger(
        type=TriggerType(rule_data.trigger.type.upper()),
        config=rule_data.trigger.config
    )
    
    conditions = [
        Condition(
            field=cond.field,
            operator=cond.operator,
            value=cond.value
        )
        for cond in rule_data.conditions
    ]
    
    actions = [
        Action(
            name=action.name,
            queue=action.queue,
            payload=action.payload,
            tenant_id=action.tenant_id,
            priority=action.priority,
            max_attempts=action.max_attempts
        )
        for action in rule_data.actions
    ]
    
    rule = AutomationRule.create(
        name=rule_data.name,
        description=rule_data.description,
        tenant_id=tenant_id,
        trigger=trigger,
        actions=actions,
        created_by=created_by,
        conditions=conditions,
        tags=rule_data.tags or {}
    )
    
    await repo.add(rule)
    return rule

@router.get("/{rule_id}", response_model=AutomationRuleResponse)
async def get_rule(
    rule_id: UUID,
    tenant_id: str = "default-tenant",
    repo: AutomationRuleRepository = Depends(get_automation_rule_repository),
):
    # Get an automation rule by ID.
    rule = await repo.get_by_id(rule_id, tenant_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.get("", response_model=List[AutomationRuleResponse])
async def list_rules(
    tenant_id: str = "default-tenant",
    enabled: Optional[bool] = None,
    trigger_type: Optional[str] = None,
    repo: AutomationRuleRepository = Depends(get_automation_rule_repository),
):
    # List all automation rules for a tenant.
    return await repo.list_by_tenant(
        tenant_id=tenant_id,
        enabled=enabled,
        trigger_type=trigger_type
    )

@router.put("/{rule_id}", response_model=AutomationRuleResponse)
async def update_rule(
    rule_id: UUID,
    rule_data: AutomationRuleUpdate,
    tenant_id: str = "default-tenant",
    repo: AutomationRuleRepository = Depends(get_automation_rule_repository),
):
    # Update an existing automation rule.
    # Get existing rule
    existing = await repo.get_by_id(rule_id, tenant_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Create updated rule
    updated = AutomationRule(
        id=existing.id,
        name=rule_data.name or existing.name,
        description=rule_data.description if rule_data.description is not None else existing.description,
        tenant_id=existing.tenant_id,
        enabled=rule_data.enabled if rule_data.enabled is not None else existing.enabled,
        trigger=Trigger(
            type=TriggerType(rule_data.trigger.type.upper()) if rule_data.trigger else existing.trigger.type,
            config=rule_data.trigger.config if rule_data.trigger else existing.trigger.config
        ) if rule_data.trigger else existing.trigger,
        conditions=[
            Condition(
                field=cond.field,
                operator=cond.operator,
                value=cond.value
            )
            for cond in (rule_data.conditions or existing.conditions)
        ],
        actions=[
            Action(
                name=action.name,
                queue=action.queue,
                payload=action.payload,
                tenant_id=action.tenant_id,
                priority=action.priority,
                max_attempts=action.max_attempts
            )
            for action in (rule_data.actions or existing.actions)
        ],
        created_at=existing.created_at,
        updated_at=datetime.utcnow(),
        created_by=existing.created_by,
        tags=rule_data.tags if rule_data.tags is not None else existing.tags
    )
    
    await repo.update(updated)
    return updated

@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    tenant_id: str = "default-tenant",
    repo: AutomationRuleRepository = Depends(get_automation_rule_repository),
):
    # Delete an automation rule.
    success = await repo.delete(rule_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return None
