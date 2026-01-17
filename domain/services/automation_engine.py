# domain/services/automation_engine.py

from typing import List, Dict, Any, Optional
import logging

from domain.models.automation_rule import AutomationRule, TriggerType
from domain.models.job import Job
from domain.ports.automation_rule_repository import AutomationRuleRepository
from domain.ports.job_repository import JobRepository

logger = logging.getLogger(__name__)

class AutomationEngine:
    """
    Core service for evaluating automation rules and triggering actions.
    """
    
    def __init__(
        self,
        rule_repository: AutomationRuleRepository,
        job_repository: JobRepository,
    ):
        self.rule_repository = rule_repository
        self.job_repository = job_repository
    
    async def handle_event(
        self,
        event_type: str,
        context: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> List[Job]:
        """
        Handle an event by evaluating all relevant automation rules.
        
        Args:
            event_type: Type of event (e.g., 'cron.daily', 'job.completed')
            context: Event context data for condition evaluation
            tenant_id: Optional tenant ID to filter rules
            
        Returns:
            List of jobs created by triggered rules
        """
        # Get all rules that match the event type
        rules = await self._get_relevant_rules(event_type, tenant_id)
        if not rules:
            return []
        
        created_jobs = []
        
        for rule in rules:
            try:
                # Check if conditions are met
                if not rule.evaluate_conditions(context):
                    continue
                    
                # Generate and save jobs for this rule
                jobs = rule.generate_jobs()
                for job in jobs:
                    await self.job_repository.add(job)
                
                created_jobs.extend(jobs)
                
                logger.info(
                    f"Triggered automation rule '{rule.name}' ({rule.id}), "
                    f"created {len(jobs)} jobs"
                )
                
            except Exception as e:
                logger.exception(
                    f"Error processing automation rule {rule.id}: {str(e)}"
                )
        
        return created_jobs
    
    async def _get_relevant_rules(
        self,
        event_type: str,
        tenant_id: Optional[str] = None,
    ) -> List[AutomationRule]:
        """Get all rules that should be evaluated for the given event type."""
        # Determine the trigger type based on event_type
        if event_type.startswith('cron.'):
            trigger_type = TriggerType.CRON
        elif event_type.startswith('webhook.'):
            trigger_type = TriggerType.WEBHOOK
        else:
            trigger_type = TriggerType.INTERNAL_EVENT
        
        # Get all enabled rules for this trigger type and tenant
        rules = await self.rule_repository.list_by_tenant(
            tenant_id=tenant_id,
            enabled=True,
            trigger_type=trigger_type.value if trigger_type else None,
        )
        
        # Filter rules based on more specific event matching
        # (e.g., specific cron pattern or webhook path)
        relevant_rules = []
        for rule in rules:
            if self._matches_event(rule, event_type):
                relevant_rules.append(rule)
        
        return relevant_rules
    
    def _matches_event(self, rule: AutomationRule, event_type: str) -> bool:
        """Check if a rule's trigger matches the given event."""
        if rule.trigger.type == TriggerType.CRON:
            # For cron, check if the event_type matches the cron pattern
            # This is a simplified example - in practice, you'd use a cron parser
            return rule.trigger.config.get('schedule') == event_type
        
        elif rule.trigger.type == TriggerType.WEBHOOK:
            # For webhooks, check if the event_type matches the webhook path
            return rule.trigger.config.get('path') in event_type
        
        elif rule.trigger.type == TriggerType.INTERNAL_EVENT:
            # For internal events, check if the event_type matches
            return rule.trigger.config.get('event_type') == event_type
        
        return False
