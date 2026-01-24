from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from domain.models.automation_rule import AutomationRule, TriggerType
from domain.models.job import Job, JobState
from domain.ports.automation_rule_repository import AutomationRuleRepository
from domain.ports.job_attempt_repository import JobAttemptRepository
from domain.ports.job_repository import JobRepository


@dataclass
class QueueConfig:
    max_concurrency: int = 10
    active: bool = True


@dataclass
class TenantConfig:
    max_running_jobs: int = 5
    active: bool = True


class FakeJobRepository(JobRepository):
    def __init__(
        self,
        *,
        queues: Optional[Dict[str, QueueConfig]] = None,
        tenants: Optional[Dict[str, TenantConfig]] = None,
    ):
        self._jobs: Dict[UUID, Job] = {}
        self._queues = queues or {}
        self._tenants = tenants or {}

    async def insert(self, job: Job) -> Job:
        self._jobs[job.id] = job
        return job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    async def update(self, job: Job) -> Job:
        self._jobs[job.id] = job
        return job

    async def acquire_next_due_job(
        self,
        *,
        queue: str,
        now: datetime,
        worker_id: str,
        visibility_timeout_s: int = 300,
    ) -> Job | None:
        queue_cfg = self._queues.get(queue, QueueConfig())
        if not queue_cfg.active:
            return None

        running_in_queue = sum(
            1
            for job in self._jobs.values()
            if job.queue == queue
            and job.state == JobState.RUNNING
            and not job.archived
        )
        if running_in_queue >= queue_cfg.max_concurrency:
            return None

        candidates = [
            job
            for job in self._jobs.values()
            if job.queue == queue
            and not job.archived
            and job.state in (JobState.PENDING, JobState.SCHEDULED)
            and (job.next_run_at is None or job.next_run_at <= now)
        ]

        def tenant_allowed(job: Job) -> bool:
            if job.tenant_id is None:
                return True
            tenant_cfg = self._tenants.get(job.tenant_id, TenantConfig())
            if not tenant_cfg.active:
                return False
            running = sum(
                1
                for j in self._jobs.values()
                if j.tenant_id == job.tenant_id
                and j.state == JobState.RUNNING
                and not j.archived
            )
            return running < tenant_cfg.max_running_jobs

        candidates = [job for job in candidates if tenant_allowed(job)]

        if not candidates:
            return None

        candidates.sort(key=lambda j: (-j.priority, j.created_at))
        job = candidates[0]
        leased = job.acquire_lease(
            worker_id=worker_id,
            visibility_timeout_s=visibility_timeout_s,
            now=now,
        )
        self._jobs[job.id] = leased
        return leased

    async def find_expired_running_jobs(
        self,
        *,
        cutoff: datetime,
        limit: int = 100,
    ) -> List[Job]:
        expired = [
            job
            for job in self._jobs.values()
            if job.state == JobState.RUNNING
            and job.lease_expires_at is not None
            and job.lease_expires_at <= cutoff
        ]
        return expired[:limit]


class FakeJobAttemptRepository(JobAttemptRepository):
    def __init__(self):
        self._attempts = []

    async def insert(self, job_attempt):
        self._attempts.append(job_attempt)
        return job_attempt

    async def list_for_job(self, job_id: UUID):
        return [a for a in self._attempts if a.job_id == job_id]


class FakeAutomationRuleRepository(AutomationRuleRepository):
    def __init__(self):
        self._rules: List[AutomationRule] = []

    async def add(self, rule: AutomationRule) -> None:
        self._rules.append(rule)

    async def get_by_id(self, rule_id: UUID, tenant_id: str):
        for rule in self._rules:
            if rule.id == rule_id and rule.tenant_id == tenant_id:
                return rule
        return None

    async def list_by_tenant(self, tenant_id: str, enabled=None, trigger_type=None):
        rules = [
            rule for rule in self._rules if rule.tenant_id == tenant_id
        ]
        if enabled is not None:
            rules = [r for r in rules if r.enabled == enabled]
        if trigger_type is not None:
            rules = [r for r in rules if r.trigger.type.value == trigger_type]
        return rules

    async def update(self, rule: AutomationRule) -> None:
        for idx, existing in enumerate(self._rules):
            if existing.id == rule.id and existing.tenant_id == rule.tenant_id:
                self._rules[idx] = rule
                return

    async def delete(self, rule_id: UUID, tenant_id: str) -> bool:
        for idx, rule in enumerate(self._rules):
            if rule.id == rule_id and rule.tenant_id == tenant_id:
                del self._rules[idx]
                return True
        return False


class FakeUnitOfWork:
    def __init__(self, job_repo, job_attempt_repo, automation_rules):
        self.job_repo = job_repo
        self.job_attempt_repo = job_attempt_repo
        self.automation_rules = automation_rules

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeEventBus:
    def __init__(self):
        self.created = []

    async def publish_job_created(self, job: Job) -> None:
        self.created.append(job)

    async def publish_job_started(self, job: Job, worker_id: str) -> None:
        return None

    async def publish_job_completed(self, job: Job, execution_time_ms: int | None = None) -> None:
        return None

    async def publish_job_failed(self, job: Job, error_message: str | None = None) -> None:
        return None

    async def publish_job_dead(self, job: Job, error_message: str | None = None) -> None:
        return None

    async def publish_job_retry_scheduled(self, job: Job, next_run_at: str) -> None:
        return None
