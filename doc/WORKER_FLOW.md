# Worker End-to-End Flow

This document explains the worker runtime from startup to job completion.
It focuses on method call order and responsibilities.

## High-level flow

1) Worker starts and initializes providers.
2) Main loop polls for jobs.
3) Acquire next runnable job (DB lock + lease).
4) Validate capabilities.
5) Execute job with heartbeat.
6) Mark job success or failure.
7) Persist job attempts and state changes.

## Core classes and responsibilities

### `Worker` (`worker/core/worker.py`)
Responsibilities:
- Lifecycle management (start, loop, shutdown).
- Concurrency control (semaphore + running tasks).
- Scheduling job processing tasks.

Key methods:
- `run()`: entrypoint, sets up signals and executes the loop.
- `_run_loop()`: polling loop for capacity → acquire → process.
- `_acquire_next_job()`: calls AcquireNextJobUseCase.
- `_start_job_processing()`: starts a background task.
- `_shutdown()`: cancels tasks and logs stats.

### `WorkerProviders` (`worker/core/providers.py`)
Responsibilities:
- Dependency container (UoW, registries, use cases).
- Keeps `Worker` small and swappable in tests.

Key fields:
- `uow_factory`, `plugin_registry`, `registry_manager`
- `acquire_uc`, `complete_uc`, `fail_uc`, `heartbeat_uc`

### `JobProcessor` (`worker/core/job_processor.py`)
Responsibilities:
- Capability checks.
- Job execution + heartbeat management.
- State transitions on success/failure.

Key methods:
- `check_capabilities(job)`: rejects jobs without required capabilities.
- `process(job)`: runs dispatch + completion/failure logic.
- `_heartbeat_loop()`: extends leases while job runs.
- `_handle_job_success()` / `_handle_job_failure()` / `_handle_job_error()`

### `dispatch_job` (`worker/core/dispatcher.py`)
Responsibilities:
- Build hybrid registry (plugin + DB).
- Resolve job definition and handler.
- Execute via the correct executor.

Key steps:
- Load `JobDefinition` from hybrid registry.
- Resolve handler from `handler_ref`.
- Select executor (`python_async`, `thread_pool`, `http`).
- Run job with timeout.

### Acquire use case (`application/use_cases/acquire_next_job.py`)
Responsibilities:
- Orchestrates acquisition via repository.
  
Key call:
- `JobRepository.acquire_next_due_job(...)`

### Repository acquisition (`adapters/outbound/db/job_repository_impl.py`)
Responsibilities:
- Select eligible job with `FOR UPDATE SKIP LOCKED`.
- Enforce queue + tenant limits.
- Acquire lease (`state=RUNNING`, `locked_by`, `lease_expires_at`).

## Method call order (typical run)

1) `Worker.run()`
2) `Worker._run_loop()`
3) `Worker._acquire_next_job()`
4) `AcquireNextJobUseCase.execute()`
5) `JobRepository.acquire_next_due_job()`
6) `Worker._start_job_processing()`
7) `JobProcessor.check_capabilities()`
8) `JobProcessor.process()`
9) `dispatch_job(...)`
10) `Executor.execute(...)`
11) `CompleteJobUseCase.execute()` OR `FailJobUseCase.execute()`

## Lease + heartbeat behavior

- On acquire: job moves to RUNNING + `lease_expires_at = now + visibility_timeout`.
- While running: heartbeat extends `lease_expires_at`.
- If worker crashes: reclaim job via `ReclaimExpiredJobsUseCase`.

## Concurrency and fairness

- Worker semaphore limits active jobs per worker.
- Queue-level `max_concurrency` enforced in repository.
- Tenant-level `max_running_jobs` enforced in repository.

## Failure and retry

- Failures call `Job.apply_failure()` with retry policy.
- If attempts remain → `SCHEDULED` with `next_run_at`.
- If attempts exhausted → `DEAD`.

## Observability (logs)

Key log points:
- acquisition attempt and lease info
- execution mode and handler
- success/failure state
- queue/tenant concurrency limit reached
