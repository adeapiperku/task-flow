# TaskFlow

TaskFlow is a **job automation engine** for backend developers.

It provides:

- **Job scheduling & execution**
- **Intelligent retries**
- **Worker orchestration & queues**
- **Clean HTTP APIs and a clear domain model**

Unlike a simple “background task” helper, TaskFlow:

- Tracks a **stateful job lifecycle**  
  `PENDING → SCHEDULED → RUNNING → SUCCEEDED / FAILED / DEAD / CANCELLED`
- Is **multi-tenant** and **queue-based**
- Supports **automation rules** (triggers, conditions, actions)
- Is designed to be **auditable** (logs, attempts, transitions)

TaskFlow is designed as a real product, not a one-off script.

---

## Architecture Overview

TaskFlow follows hexagonal architecture / DDD principles.

### Domain Layer

Core domain objects (present and planned):

- **Job** – aggregate root (already implemented)
- **JobState** – lifecycle enum
- **JobAttempt** – individual execution attempts (for retries & logs, planned)
- **Queue** – logical grouping with priorities and limits (planned)
- **AutomationRule** – “when X happens, create these jobs” (planned)
- **Worker lease / lock** – safe distributed worker coordination (planned)

### Application Layer (Use Cases)

Use cases orchestrate domain logic and persistence behind ports (interfaces):

- `ScheduleJobUseCase` ✅
- `GetJobByIdUseCase` (planned)
- `ListJobsUseCase` (planned; filters by tenant, queue, state, etc.)
- `CancelJobUseCase` (planned)
- `RetryJobUseCase` (planned)
- `DefineAutomationRuleUseCase` (planned)
- `TriggerAutomationUseCase` (for webhooks/events, planned)

### Adapters

**Inbound:**

- FastAPI HTTP API (current)
- Future: CLI, webhook receiver, gRPC, etc.

**Outbound:**

- Postgres via async SQLAlchemy (current)
- Future: broker/queue backends (e.g. Redis)
- Future: metrics/observability (Prometheus, OpenTelemetry)
- Future: HTTP executor for calling external services

All application code talks to ports, not directly to frameworks.

---

## What Makes TaskFlow Different?

TaskFlow is not just “another Celery/RQ clone”. Its design focuses on:

### 1. First-Class Domain Model & Auditability

Jobs are **entities with a lifecycle**, not just messages:

- Full history: attempts, state transitions, timestamps
- Clear state machine:
  `PENDING → SCHEDULED → RUNNING → SUCCEEDED / FAILED / DEAD / CANCELLED`
- Ability to introspect *why* a job failed or died:
  attempts, errors, backoff decisions, lock info

### 2. Automation Rules as Domain Objects

TaskFlow is not limited to “push jobs via API”. It supports **automation**:

- `AutomationRule` with:
  - **Triggers** – time-based (cron), event-based (webhook), or internal (e.g. job finished)
  - **Conditions** – filters on tenant, payload, time, etc.
  - **Actions** – one or more job templates to enqueue

Example rule:

> “Every day at 07:00, for each tenant with `plan = pro`, enqueue a `RecalculateBilling` job if their usage changed.”

### 3. Intelligent Retries & Scheduling

Retries are modeled as part of the domain, not hidden config.

- Pluggable `RetryPolicy`:
  - max attempts
  - strategy (fixed, linear, exponential, jitter)
  - base delay
- Dead-letter queues for jobs that exceed their retry budget
- `next_run_at` scheduling integrated into the job model

### 4. Multi-Tenant Fairness & Limits

Multi-tenancy is a first-class concern:

- Per-tenant concurrency limits (e.g. max N running jobs per tenant)
- Per-queue concurrency limits (e.g. dedicated workers per queue)
- Fair scheduling so noisy tenants cannot starve others

### 5. Observability Built-In

From the start, TaskFlow is designed for visibility:

- Metrics:
  - queue depth
  - throughput
  - success/failure rate
  - latency per queue
  - retries per job
- Event log per job (for UI / debugging)
- Correlation IDs from request → job → sub-jobs

---

## Implementation Roadmap

High-level roadmap of how TaskFlow is being built.

### ✅ Phase 0 – Foundation (current)

- Job domain model + `JobOrm`
- Postgres + Alembic migrations
- SQLAlchemy `Base` + async session factory
- `JobRepositorySqlAlchemy` (insert implemented)
- `UnitOfWork` abstraction + `SqlAlchemyUnitOfWork`
- `ScheduleJobUseCase`
- FastAPI app with `POST /jobs`
- Global error handling with an `AppError` hierarchy

> Minor hardening: ensure migrations match `JobOrm` exactly, add simple `/health` endpoint.

---

### 🟡 Phase 1 – Job Querying & Lifecycle Basics

Goal: **See and query what was scheduled.**

- Repository:
  - `get_by_id(job_id)` (done)
  - later: search with filters (tenant, queue, state, pagination)
- Application:
  - `GetJobByIdUseCase`
  - later: `ListJobsUseCase`
- API:
  - `GET /jobs/{id}` returning `JobResponse`
  - optional: `GET /jobs?state=PENDING&queue=default`

This makes the system feel real: schedule a job, then fetch it and see its current state.

---

### 🟡 Phase 2 – Worker & Scheduler Loop

Goal: **Jobs don’t just sit in the DB; workers execute them.**

- Domain:
  - Finish `JobState` transitions
  - Fields like `next_run_at`, `last_error_message`, `last_error_type`
- Repository:
  - `acquire_next_due_job(queue, now, worker_id)` using:
    - `state in (PENDING, SCHEDULED)`
    - `next_run_at <= now`
    - row-level locking (`FOR UPDATE SKIP LOCKED`)
- Application:
  - `AcquireNextJobUseCase`
  - `CompleteJobUseCase`, `FailJobUseCase`
- Worker process:
  - Async loop that acquires jobs, dispatches to handlers, and updates state

This is already partially implemented.

---

### 🟡 Phase 3 – Retries & Error Policies

Goal: **Make jobs robust.**

- Domain:
  - `RetryPolicy` value object
  - optional `JobAttempt` entity
- Use cases:
  - On failure:
    - increment attempts
    - compute new `next_run_at` based on retry policy
    - change state to `SCHEDULED` or `DEAD`
- API:
  - `POST /jobs/{id}/retry` (manual retry)
  - `POST /jobs/{id}/cancel` (manual cancellation)

---

### 🟡 Phase 4 – Automation Rules

Goal: **Move from manual scheduling to real automation.**

- Domain:
  - `AutomationRule` aggregate:
    - `id`, `tenant_id`
    - trigger type: `CRON`, `WEBHOOK`, `INTERNAL_EVENT`
    - conditions
    - action templates (job definitions)
  - Trigger value objects:
    - `CronTrigger`
    - `WebhookTrigger`
    - `EventTrigger` (e.g. `job_succeeded: job_type=X`)
- Use cases:
  - `CreateAutomationRuleUseCase`
  - `ListAutomationRulesUseCase`
  - `HandleWebhookEventUseCase` → evaluate rules → enqueue jobs
- API:
  - `POST /automation-rules`
  - `GET /automation-rules`
  - `POST /events/webhook/{key}`

---

### 🟡 Phase 5 – Multi-Tenant Fairness & Limits

Goal: **Production-ready multi-tenant behavior.**

- Optional `tenant_limits` table
- Worker polling respects:
  - per-tenant running job limits
  - per-queue concurrency caps

---

### 🟡 Phase 6 – Observability & Admin

Goal: **Operate TaskFlow in production.**

- Metrics (Prometheus):
  - queue depth
  - success/failure rates
  - execution latency
  - retries per job
- Structured logging with `job_id` / `tenant_id`
- Admin endpoints:
  - `GET /admin/queues`
  - `GET /admin/automations`

---

## Next Immediate Step

The next concrete step in the implementation is:

> **Phase 1 – implement `GetJobByIdUseCase` and `GET /jobs/{id}`.**

This completes the basic lifecycle loop:

1. `POST /jobs` → schedule a job  
2. Worker picks and executes the job  
3. `GET /jobs/{id}` → observe current/final state

From there, retries, automation rules, and multi-tenant controls can be layered on top without changing the core architecture.
