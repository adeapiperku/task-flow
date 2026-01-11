# TaskFlow – Execution, Registry, and Worker Architecture

This document describes the **current state of TaskFlow’s job execution architecture**, including registries, executors, workers, leasing/heartbeats, and reclaiming logic. It is intended for developers and contributors who need to understand *how the system works end-to-end* and *why these abstractions exist*.

---

## 1. Core Mental Model

TaskFlow separates concerns into four clear layers:

1. **Job Definition (WHAT)** – What a job is, how it should run
2. **Job Run (WHEN)** – A concrete execution request stored in the database
3. **Registry (HOW)** – Explains a job to a worker (definition + handler)
4. **Worker / Executor (WHO)** – Executes jobs safely and scalably

The database is the **coordination point** between schedulers and workers. Registries are the **knowledge layer** that allows workers to remain generic.

---

## 2. Job Definitions vs Job Runs

### JobDefinition

A `JobDefinition` describes a *type of job*:
- name (e.g. `goals.daily_check`)
- handler reference (import path or URL)
- execution mode (python_async, thread_pool, http, …)
- timeout
- retry limits / policy

Definitions come from:
- **Code** (plugin / decorator registration)
- **Database** (`job_definitions` table)

### Job (Job Run)

A `Job` row represents *one execution attempt*:
- job name
- payload
- state (QUEUED, RUNNING, COMPLETED, FAILED)
- lease information
- attempt counters

Job runs are **always stored in the database** so work is durable, retryable, and distributable across workers.

---

## 3. Registry System (Key Abstraction)

The **Job Registry** answers a single question for the worker:

> “Given a job name, how do I run it?”

### 3.1 JobRegistry Port

The `JobRegistry` protocol defines three responsibilities:
- `get_definition(job_name)` – fetch job metadata
- `resolve_handler(handler_ref)` – load executable code
- `get_handler(job_name)` – convenience method

This keeps workers independent of storage or import mechanisms.

### 3.2 Plugin Registry

**Purpose:** represent jobs defined in code.

- Built from decorators, static definitions, or installed packages
- Uses importlib to resolve `module:function`
- Long-lived, in-memory

This is the *developer-owned* source of truth.

### 3.3 Database Registry

**Purpose:** represent runtime configuration.

- Reads `job_definitions` from DB
- Provides timeouts, retries, execution mode overrides
- Session-scoped (created via Unit of Work)

This is the *platform / ops-owned* source of truth.

### 3.4 Hybrid Registry

**Purpose:** combine plugin + DB.

Rule:
- If `prefer_db=True`: DB overrides code
- Otherwise: code defaults, DB fallback

Hybrid registry is what **workers actually use**. It allows:
- code to define what is possible
- DB to define how it behaves *right now*

---

## 4. Executor Layer (HOW execution happens)

The **Executor** abstraction makes `execution_mode` real.

### 4.1 Executor Port

Executors implement a single method:

```
execute(handler, payload, timeout_s) -> ExecutionResult
```

This allows the same job to run in different environments.

### 4.2 Implemented Executors

#### PythonAsyncExecutor
- Default executor
- Runs async Python handlers
- Uses `asyncio.wait_for` for timeouts

#### ThreadPoolExecutor
- Runs blocking / sync code
- Uses `run_in_executor`
- Prevents event-loop blocking

#### HttpExecutor
- Executes jobs via HTTP POST
- Handler is a URL (or callable returning URL)
- Enables cross-service job execution

Executors are chosen **per job** based on `execution_mode` in the job definition.

---

## 5. Worker Flow

The worker is intentionally **dumb and generic**.

### Worker Loop

1. Acquire next job from DB (`AcquireNextJobUseCase`)
2. Build Hybrid Registry (plugin + DB)
3. Ask registry for definition + handler
4. Select executor based on `execution_mode`
5. Execute job
6. Mark job completed or failed

The worker does **not** know job types, business logic, or schedules.

---

## 6. Leasing, Heartbeats, and Safety

### 6.1 Lease on Acquire

When a job is acquired:
- state → RUNNING
- `locked_by` set to worker_id
- `lease_expires_at = now + visibility_timeout`

This prevents other workers from picking it.

### 6.2 Heartbeat

`HeartbeatJobUseCase`:
- Extends `lease_expires_at`
- Called periodically while job is running
- Prevents premature reclaim

### 6.3 Reclaim Expired Jobs

`ReclaimExpiredJobsUseCase`:
- Finds RUNNING jobs with expired leases
- Requeues them safely
- Protects against worker crashes

This enables **at-least-once execution** semantics.

---

## 7. Why the Database Is Central

The DB is not an implementation detail – it is the **coordination layer**:

- Scheduler inserts job runs
- Workers compete for jobs safely
- Retries and crashes are recoverable
- State is inspectable and auditable

Without DB-backed job runs, none of the following are possible:
- horizontal scaling
- crash recovery
- retries
- observability

---

## 8. What This Architecture Enables

With what is implemented now, TaskFlow supports:

- Generic workers (no job knowledge)
- Pluggable job libraries
- Runtime configuration via DB
- Multiple execution strategies
- Safe distributed execution
- Future features (scheduling, fairness, rate limits)

---

## 9. Next Logical Extensions

The current architecture cleanly supports adding:

1. Scheduler / Cron subsystem
2. Retry backoff engine
3. Worker concurrency limits
4. Capability-based routing
5. Container / K8s executors

No refactor required – only extensions.

---

## 10. One-Sentence Summary

**TaskFlow turns job execution into a data-driven, pluggable runtime where developers define jobs in code, the platform defines execution rules in data, and workers execute blindly and safely.**
