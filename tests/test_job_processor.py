from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from domain.models.job import Job
from domain.ports.executor import ExecutionResult
from tests.fakes import FakeJobAttemptRepository, FakeJobRepository
from worker.core.job_processor import JobProcessor


class _FakeRegistryManager:
    def __init__(self, capabilities):
        self._capabilities = capabilities

    async def get_job_definition(self, job_name: str):
        return type("JobDef", (), {"capabilities": self._capabilities})


class _FakeCompleteUC:
    def __init__(self):
        self.called = False

    async def execute(self, *args, **kwargs):
        self.called = True


class _FakeFailUC:
    def __init__(self):
        self.called = False

    async def execute(self, *args, **kwargs):
        self.called = True


class _FakeHeartbeatUC:
    async def execute(self, *args, **kwargs):
        return None


@dataclass
class _FakeProviders:
    uow_factory: object
    plugin_registry: object
    registry_manager: object
    complete_uc: object
    fail_uc: object
    heartbeat_uc: object


@dataclass
class _FakeConfig:
    worker_id: str
    capabilities: set[str]
    prefer_db: bool
    heartbeat_interval_s: float


@pytest.mark.asyncio
async def test_job_processor_success(monkeypatch, caplog):
    job = Job.new(name="send-email", payload={"email": "a@b.com"})

    async def _dispatch_job(**kwargs):
        return ExecutionResult(success=True)

    monkeypatch.setattr("worker.core.job_processor.dispatch_job", _dispatch_job)

    providers = _FakeProviders(
        uow_factory=lambda: None,
        plugin_registry=None,
        registry_manager=_FakeRegistryManager([]),
        complete_uc=_FakeCompleteUC(),
        fail_uc=_FakeFailUC(),
        heartbeat_uc=_FakeHeartbeatUC(),
    )
    config = _FakeConfig(
        worker_id="worker-1",
        capabilities=set(),
        prefer_db=True,
        heartbeat_interval_s=0.01,
    )
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    processor = JobProcessor(
        config=config,
        providers=providers,
        stats=type("Stats", (), {"jobs_processed": 0, "jobs_succeeded": 0, "jobs_failed": 0, "jobs_rejected": 0})(),
        semaphore=asyncio.Semaphore(1),
        shutdown_event=shutdown_event,
    )

    with caplog.at_level("INFO"):
        await processor.process(job)

    assert providers.complete_uc.called is True
    assert providers.fail_uc.called is False
    assert "succeeded" in caplog.text


@pytest.mark.asyncio
async def test_job_processor_capability_reject(monkeypatch, caplog):
    job = Job.new(name="send-email", payload={"email": "a@b.com"})

    providers = _FakeProviders(
        uow_factory=lambda: None,
        plugin_registry=None,
        registry_manager=_FakeRegistryManager(["gpu"]),
        complete_uc=_FakeCompleteUC(),
        fail_uc=_FakeFailUC(),
        heartbeat_uc=_FakeHeartbeatUC(),
    )
    config = _FakeConfig(
        worker_id="worker-1",
        capabilities={"cpu"},
        prefer_db=True,
        heartbeat_interval_s=0.01,
    )
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    processor = JobProcessor(
        config=config,
        providers=providers,
        stats=type("Stats", (), {"jobs_processed": 0, "jobs_succeeded": 0, "jobs_failed": 0, "jobs_rejected": 0})(),
        semaphore=asyncio.Semaphore(1),
        shutdown_event=shutdown_event,
    )

    with caplog.at_level("WARNING"):
        allowed = await processor.check_capabilities(job)

    assert allowed is False
    assert providers.fail_uc.called is True
    assert "missing capabilities" in caplog.text
