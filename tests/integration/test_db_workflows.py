from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import text

from application.dto.schedule_job_command import ScheduleJobCommand
from application.use_cases.acquire_next_job import AcquireNextJobUseCase
from application.use_cases.complete_job import CompleteJobUseCase
from application.use_cases.fail_job import FailJobUseCase
from application.use_cases.handle_event import HandleEventUseCase
from application.use_cases.reclaim_expired_jobs import ReclaimExpiredJobsUseCase
from application.use_cases.schedule_job import ScheduleJobUseCase
from domain.models.job import JobState
from domain.models.automation_rule import Action, AutomationRule, Condition, Trigger, TriggerType
from tests.fakes import FakeEventBus


def _require_db():
    if not os.environ.get("TASKFLOW_DATABASE_URL"):
        pytest.skip("TASKFLOW_DATABASE_URL not set")


async def _reset_db():
    from adapters.outbound.db.base import AsyncSessionLocal, reset_engine

    await reset_engine(use_null_pool=True)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE "
                "job_attempts, jobs, job_definitions, "
                "automation_rule_actions, automation_rule_conditions, automation_rules, "
                "queues, tenants "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()


async def _seed_queue_and_tenant():
    from adapters.outbound.db.base import AsyncSessionLocal, reset_engine

    await reset_engine(use_null_pool=True)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO queues (name, max_concurrency, active) "
                "VALUES ('default', 1, true) "
                "ON CONFLICT (name) DO UPDATE "
                "SET max_concurrency = EXCLUDED.max_concurrency, active = EXCLUDED.active"
            )
        )
        await session.execute(
            text(
                "INSERT INTO tenants (id, name, max_running_jobs, active) "
                "VALUES ('11111111-1111-1111-1111-111111111111', 'demo-tenant', 1, true) "
                "ON CONFLICT (id) DO UPDATE "
                "SET max_running_jobs = EXCLUDED.max_running_jobs, active = EXCLUDED.active"
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_db_schedule_acquire_complete():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    schedule = ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    cmd = ScheduleJobCommand(
        name="send-email",
        payload={"email": "demo@example.com", "subject": "Hello"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        priority=0,
        max_attempts=3,
        scheduled_at=datetime.utcnow(),
    )
    job = await schedule.execute(cmd)

    acquire = AcquireNextJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    leased = await acquire.execute(queue="default", worker_id="worker-test")
    assert leased is not None
    assert leased.state.value == "RUNNING"

    complete = CompleteJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    now = datetime.utcnow()
    await complete.execute(
        job.id,
        started_at=now,
        finished_at=now,
        worker_id="worker-test",
    )

    from adapters.outbound.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                text("SELECT state, attempts FROM jobs WHERE id = :id"),
                {"id": str(job.id)},
            )
        ).first()
        assert row[0] == "SUCCEEDED"
        assert row[1] == 1

        attempts = (
            await session.execute(
                text("SELECT count(*) FROM job_attempts WHERE job_id = :id"),
                {"id": str(job.id)},
            )
        ).scalar_one()
    assert attempts == 1


@pytest.mark.asyncio
async def test_db_acquire_logs_lease(caplog):
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    schedule = ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    cmd = ScheduleJobCommand(
        name="send-email",
        payload={"email": "demo@example.com", "subject": "Hello"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        scheduled_at=datetime.utcnow(),
    )
    await schedule.execute(cmd)

    acquire = AcquireNextJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    with caplog.at_level("INFO"):
        leased = await acquire.execute(queue="default", worker_id="worker-test")
    assert leased is not None
    assert "leased job_id" in caplog.text


@pytest.mark.asyncio
async def test_db_queue_concurrency_limit():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    schedule = ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    cmd1 = ScheduleJobCommand(
        name="process-image",
        payload={"image_id": "img_A"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        scheduled_at=datetime.utcnow(),
    )
    cmd2 = ScheduleJobCommand(
        name="process-image",
        payload={"image_id": "img_B"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        scheduled_at=datetime.utcnow(),
    )
    await schedule.execute(cmd1)
    await schedule.execute(cmd2)

    acquire = AcquireNextJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    first = await acquire.execute(queue="default", worker_id="worker-1")
    assert first is not None
    second = await acquire.execute(queue="default", worker_id="worker-2")
    assert second is None


@pytest.mark.asyncio
async def test_db_tenant_concurrency_limit():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE queues SET max_concurrency = 10 WHERE name = 'default'")
        )
        await session.commit()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    schedule = ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    cmd1 = ScheduleJobCommand(
        name="process-image",
        payload={"image_id": "tenant_A"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        scheduled_at=datetime.utcnow(),
    )
    cmd2 = ScheduleJobCommand(
        name="process-image",
        payload={"image_id": "tenant_B"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        scheduled_at=datetime.utcnow(),
    )
    await schedule.execute(cmd1)
    await schedule.execute(cmd2)

    acquire = AcquireNextJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    first = await acquire.execute(queue="default", worker_id="worker-1")
    assert first is not None
    second = await acquire.execute(queue="default", worker_id="worker-2")
    assert second is None


@pytest.mark.asyncio
async def test_db_fail_and_retry_dead():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    schedule = ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    cmd = ScheduleJobCommand(
        name="send-email",
        payload={"email": "demo@example.com"},
        queue="default",
        tenant_id="11111111-1111-1111-1111-111111111111",
        max_attempts=2,
        scheduled_at=datetime.utcnow(),
    )
    job = await schedule.execute(cmd)

    fail = FailJobUseCase(uow_factory=SqlAlchemyUnitOfWork)
    now = datetime.utcnow()
    first = await fail.execute(
        job.id,
        started_at=now,
        finished_at=now,
        worker_id="worker-test",
        error_type="ValueError",
        error_message="boom",
    )
    assert first.state == JobState.SCHEDULED

    second = await fail.execute(
        job.id,
        started_at=now,
        finished_at=now,
        worker_id="worker-test",
        error_type="ValueError",
        error_message="boom",
    )
    assert second.state == JobState.DEAD


@pytest.mark.asyncio
async def test_db_reclaim_expired_jobs():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO jobs (id, queue, name, tenant_id, payload, state, priority, "
                "created_at, updated_at, scheduled_at, next_run_at, attempts, max_attempts, "
                "archived, locked_by, locked_at, lease_expires_at, retry_strategy, retry_base_delay_seconds) "
                "VALUES (gen_random_uuid(), 'default', 'send-email', "
                "'11111111-1111-1111-1111-111111111111', "
                "'{\"email\":\"demo@example.com\"}', 'RUNNING', 0, "
                "now(), now(), now(), now(), 0, 3, false, "
                "'worker-test', now(), now() - interval '5 minutes', "
                "'EXPONENTIAL', 30)"
            )
        )
        await session.commit()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
    reclaim = ReclaimExpiredJobsUseCase(uow_factory=SqlAlchemyUnitOfWork)
    reclaimed = await reclaim.execute(grace_period_s=0, max_reclaim=10)
    assert reclaimed
    assert reclaimed[0].state == JobState.SCHEDULED


@pytest.mark.asyncio
async def test_db_automation_rule_creates_job():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    trigger = Trigger(type=TriggerType.WEBHOOK, config={"path": "webhook.demo"})
    conditions = [Condition(field="plan", operator="eq", value="pro")]
    actions = [
        Action(
            name="send-email",
            queue="default",
            payload={"email": "demo@example.com"},
        )
    ]
    rule = AutomationRule.create(
        name="demo-rule",
        description="Trigger job on webhook",
        tenant_id="11111111-1111-1111-1111-111111111111",
        trigger=trigger,
        actions=actions,
        created_by="system",
        conditions=conditions,
    )

    async with SqlAlchemyUnitOfWork() as uow:
        await uow.automation_rules.add(rule)

    use_case = HandleEventUseCase(
        uow_factory=SqlAlchemyUnitOfWork,
        event_bus=FakeEventBus(),
    )
    jobs = await use_case.execute(
        event_type="webhook.demo",
        context={"plan": "pro"},
        tenant_id="11111111-1111-1111-1111-111111111111",
    )
    assert len(jobs) == 1
    assert jobs[0].name == "send-email"


@pytest.mark.asyncio
async def test_db_automation_rule_no_match():
    _require_db()
    await _reset_db()
    await _seed_queue_and_tenant()

    from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork

    trigger = Trigger(type=TriggerType.WEBHOOK, config={"path": "webhook.demo"})
    conditions = [Condition(field="plan", operator="eq", value="pro")]
    actions = [
        Action(
            name="send-email",
            queue="default",
            payload={"email": "demo@example.com"},
        )
    ]
    rule = AutomationRule.create(
        name="demo-rule",
        description="Trigger job on webhook",
        tenant_id="11111111-1111-1111-1111-111111111111",
        trigger=trigger,
        actions=actions,
        created_by="system",
        conditions=conditions,
    )

    async with SqlAlchemyUnitOfWork() as uow:
        await uow.automation_rules.add(rule)

    use_case = HandleEventUseCase(
        uow_factory=SqlAlchemyUnitOfWork,
        event_bus=FakeEventBus(),
    )
    jobs = await use_case.execute(
        event_type="webhook.demo",
        context={"plan": "free"},
        tenant_id="11111111-1111-1111-1111-111111111111",
    )

    assert jobs == []
