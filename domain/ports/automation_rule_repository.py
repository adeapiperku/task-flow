# domain/ports/automation_rule_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from domain.models.automation_rule import AutomationRule


class AutomationRuleRepository(ABC):
    """Interface for persisting and retrieving AutomationRules."""
    
    @abstractmethod
    async def add(self, rule: AutomationRule) -> None:
        """Add a new automation rule."""
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_id(self, rule_id: UUID, tenant_id: str) -> Optional[AutomationRule]:
        """Retrieve a rule by ID and tenant ID."""
        raise NotImplementedError
    
    @abstractmethod
    async def list_by_tenant(
        self, 
        tenant_id: str, 
        enabled: Optional[bool] = None,
        trigger_type: Optional[str] = None
    ) -> List[AutomationRule]:
        """List all rules for a tenant, optionally filtered by enabled status and trigger type."""
        raise NotImplementedError
    
    @abstractmethod
    async def update(self, rule: AutomationRule) -> None:
        """Update an existing rule."""
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, rule_id: UUID, tenant_id: str) -> bool:
        """Delete a rule by ID and tenant ID. Returns True if deleted, False if not found."""
        raise NotImplementedError
