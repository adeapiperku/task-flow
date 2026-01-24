from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from application.use_cases.handle_event import HandleEventUseCase
from domain.models.automation_rule import Action, AutomationRule, Condition, Trigger, TriggerType
from domain.models.job import Job, JobState
from domain.models.retry_policy import RetryStrategy
from tests.fakes import (
    FakeAutomationRuleRepository,
    FakeEventBus,
    FakeJobAttemptRepository,
    FakeJobRepository,
    FakeUnitOfWork,
    QueueConfig,
    TenantConfig,
)


@pytest.mark.asyncio
async def test_complete_job_success():
    job_repo = FakeJobRepository()
    attempts_repo = FakeJobAttemptRepository()
    rules_repo = FakeAutomationRuleRepository()

    job = Job.new(name="send-email", payload={"email": "a@b.com"})
    await job_repo.insert(job)

    uow_factory = lambda: FakeUnitOfWork(job_repo, attempts_repo, rules_repo)
    use_case = CompleteJobUseCase(uow_factory=uow_factory)

    now = datetime.utcnow()
    result = await use_case.execute(
        job.id,
        started_at=now,
        finished_at=now,
        worker_id="worker-1",
    )

    assert result.state == JobState.SUCCEEDED
    assert result.attempts == 1
    attempts = await attempts_repo.list_for_job(job.id)
    assert len(attempts) == 1
    assert attempts[0].success is True


@pytest.mark.asyncio
async def test_fail_job_retries_and_dead():
    job_repo = FakeJobRepository()
    attempts_repo = FakeJobAttemptRepository()
    rules_repo = FakeAutomationRuleRepository()

    job = Job.new(
        name="send-email",
        payload={"email": "a@b.com"},
        max_attempts=2,
        retry_strategy=RetryStrategy.FIXED,
        retry_base_delay_seconds=1,
    )
    await job_repo.insert(job)

    uow_factory = lambda: FakeUnitOfWork(job_repo, attempts_repo, rules_repo)
    use_case = FailJobUseCase(uow_factory=uow_factory)

    now = datetime.utcnow()
    first = await use_case.execute(
        job.id,
        started_at=now,
        finished_at=now,
        worker_id="worker-1",
        error_type="ValueError",
        error_message="boom",
    )
    assert first.state == JobState.SCHEDULED
    assert first.attempts == 1

    second = await use_case.execute(
        job.id,
        started_at=now,
        finished_at=now,
        worker_id="worker-1",
        error_type="ValueError",
        error_message="boom",
    )
    assert second.state == JobState.DEAD
    assert second.attempts == 2

    attempts = await attempts_repo.list_for_job(job.id)
    assert len(attempts) == 2


@pytest.mark.asyncio
async def test_acquire_respects_queue_and_tenant_limits():
    queues = {"default": QueueConfig(max_concurrency=1, active=True)}
    tenants = {"t1": TenantConfig(max_running_jobs=1, active=True)}
    job_repo = FakeJobRepository(queues=queues, tenants=tenants)
    attempts_repo = FakeJobAttemptRepository()
    rules_repo = FakeAutomationRuleRepository()

    now = datetime.utcnow() - timedelta(seconds=1)
    job1 = Job.new(name="send-email", payload={"email": "a@b.com"}, tenant_id="t1")
    job2 = Job.new(name="send-email", payload={"email": "b@b.com"}, tenant_id="t1")
    await job_repo.insert(job1)
    await job_repo.insert(job2)

    uow_factory = lambda: FakeUnitOfWork(job_repo, attempts_repo, rules_repo)
    use_case = AcquireNextJobUseCase(uow_factory=uow_factory)

    first = await use_case.execute(queue="default", worker_id="w1")
    assert first is not None
    second = await use_case.execute(queue="default", worker_id="w2")
    assert second is None

    completed = first.mark_succeeded()
    await job_repo.update(completed)
    third = await use_case.execute(queue="default", worker_id="w3")
    assert third is not None


@pytest.mark.asyncio
async def test_automation_rule_creates_jobs():
    job_repo = FakeJobRepository()
    attempts_repo = FakeJobAttemptRepository()
    rules_repo = FakeAutomationRuleRepository()

    trigger = Trigger(type=TriggerType.WEBHOOK, config={"path": "webhook.demo"})
    conditions = [Condition(field="plan", operator="eq", value="pro")]
    actions = [
        Action(
            name="send-email",
            queue="default",
            payload={"email": "pro@example.com"},
        )
    ]
    rule = AutomationRule.create(
        name="demo-rule",
        description="Trigger job on webhook",
        tenant_id="t1",
        trigger=trigger,
        actions=actions,
        created_by="system",
        conditions=conditions,
    )
    await rules_repo.add(rule)

    uow_factory = lambda: FakeUnitOfWork(job_repo, attempts_repo, rules_repo)
    event_bus = FakeEventBus()
    use_case = HandleEventUseCase(uow_factory=uow_factory, event_bus=event_bus)

    jobs = await use_case.execute(
        event_type="webhook.demo",
        context={"plan": "pro"},
        tenant_id="t1",
    )

    assert len(jobs) == 1
    assert jobs[0].name == "send-email"
    assert jobs[0].tenant_id == "t1"
