# TaskFlow - Comprehensive Testing Guide

This guide provides step-by-step instructions to test all features of the TaskFlow job automation engine.

## Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Database Setup](#database-setup)
3. [Testing Architecture](#testing-architecture)
4. [Step-by-Step Testing](#step-by-step-testing)
   - [Phase 1: Basic Job Scheduling](#phase-1-basic-job-scheduling)
   - [Phase 2: Worker Execution](#phase-2-worker-execution)
   - [Phase 3: Job Registry & Executors](#phase-3-job-registry--executors)
   - [Phase 4: Capabilities & Routing](#phase-4-capabilities--routing)
   - [Phase 5: Leases & Heartbeats](#phase-5-leases--heartbeats)
   - [Phase 6: Concurrency & Backpressure](#phase-6-concurrency--backpressure)
   - [Phase 7: Retries & Error Handling](#phase-7-retries--error-handling)
   - [Phase 8: Automation Rules](#phase-8-automation-rules)

---

## Prerequisites & Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings httpx
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env

# Edit .env with your database credentials
TASKFLOW_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow
TASKFLOW_BROKER_URL=redis://localhost:6379/0
TASKFLOW_ENVIRONMENT=local
```

---

## Database Setup

### Step 1: Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE taskflow;

# Exit psql
\q
```

### Step 2: Run Migrations

```bash
# Run all migrations
python -m alembic upgrade head

# Verify migrations
python -m alembic current
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> fbafcc2f2e08, create jobs table
INFO  [alembic.runtime.migration] Running upgrade fbafcc2f2e08 -> 881e75ea5295, add retry policy columns to jobs
INFO  [alembic.runtime.migration] Running upgrade 881e75ea5295 -> ad571f39a147, add job attempts table
```

### Step 3: Verify Database Schema

```bash
# Connect to database
psql -U postgres -d taskflow

# List tables
\dt

# Check jobs table structure
\d jobs

# Check job_definitions table
\d job_definitions

# Exit
\q
```

**Expected Tables:**
- `jobs`
- `job_attempts`
- `job_definitions`
- `automation_rules` (if migrations include it)
- `automation_rule_conditions`
- `automation_rule_actions`

---

## Testing Architecture

### Component Overview

```
┌─────────────────┐
│   FastAPI API   │  ← HTTP endpoints for scheduling jobs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Use Cases     │  ← Business logic (ScheduleJob, AcquireNextJob, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Domain Layer  │  ← Job, JobDefinition, RetryPolicy, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Repositories  │  ← Database access
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘

┌─────────────────┐
│   Worker        │  ← Executes jobs from queue
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Executors     │  ← python_async, thread_pool, http
└─────────────────┘
```

---

## Step-by-Step Testing

## Phase 1: Basic Job Scheduling

### Test 1.1: Start API Server

```bash
# Terminal 1: Start FastAPI server
uvicorn adapters.inbound.api.main:app --reload --port 8000
```

**Verify:**
- Open http://localhost:8000/docs
- Should see Swagger UI with `/jobs` endpoints

### Test 1.2: Schedule a Job via API

```bash
# Terminal 2: Schedule a job
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "send-email",
    "payload": {
      "email": "test@example.com",
      "subject": "Test Email"
    },
    "queue": "default",
    "priority": 0
  }'
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "send-email",
  "state": "PENDING",
  "queue": "default",
  "priority": 0,
  "attempts": 0,
  "max_attempts": 3,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Verify in Database:**
```sql
SELECT id, name, state, queue, priority, attempts, created_at 
FROM jobs 
WHERE name = 'send-email';
```

### Test 1.3: Get Job by ID

```bash
# Replace {job_id} with actual ID from previous response
curl "http://localhost:8000/jobs/{job_id}"
```

**Expected:** Job details with current state

---

## Phase 2: Worker Execution

### Test 2.1: Start Worker

```bash
# Terminal 3: Start worker
python -m worker.runner
```

**Expected Output:**
```
INFO - Worker worker-xxx started on queue 'default' with capabilities=set(), concurrency=4
INFO - Worker worker-xxx processing job xxx (send-email, attempt 1/3)
INFO - Executing job xxx (send-email) with timeout=300s, execution_mode=python_async
[handler:email] Sending email to 'test@example.com' with subject 'Test Email'
[handler:email] Email sent to 'test@example.com'
INFO - Job xxx completed successfully in 0.30s
```

### Test 2.2: Verify Job State Change

```bash
# Check job state via API
curl "http://localhost:8000/jobs/{job_id}"
```

**Expected:** `"state": "SUCCEEDED"`

**Verify in Database:**
```sql
SELECT state, attempts, last_run_at, locked_by 
FROM jobs 
WHERE id = '{job_id}';
```

### Test 2.3: Test Multiple Jobs

```bash
# Schedule 5 jobs
for i in {1..5}; do
  curl -X POST "http://localhost:8000/jobs" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"process-image\",
      \"payload\": {\"image_id\": \"img-$i\"},
      \"queue\": \"default\"
    }"
done
```

**Observe:** Worker processes jobs concurrently (up to concurrency limit)

---

## Phase 3: Job Registry & Executors

### Test 3.1: Verify Plugin Registry

The worker uses plugin registry from `handlers/__init__.py`:

```python
# handlers/__init__.py
HANDLERS = {
    "process-image": process_image,
    "send-email": send_email,
}
```

**Test:** Jobs with these names should execute successfully.

### Test 3.2: Test Different Execution Modes

#### Python Async Executor (Default)

```bash
# Schedule job - uses python_async executor
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "send-email",
    "payload": {"email": "test@example.com"},
    "queue": "default"
  }'
```

**Verify:** Job executes with `execution_mode=python_async` in logs

#### Thread Pool Executor

To test thread pool executor, you need to:
1. Create a job definition in database with `execution_mode=thread_pool`
2. Schedule a job with that name

```sql
-- Insert job definition
INSERT INTO job_definitions (
    name, handler_ref, execution_mode, timeout_s, 
    max_attempts, backoff_policy, input_schema, 
    resource_profile, capabilities, visibility_timeout_s, version
) VALUES (
    'cpu-intensive-task',
    'handlers.cpu:heavy_computation',
    'thread_pool',
    300,
    3,
    '{}',
    '{}',
    '{}',
    '[]',
    300,
    1
);
```

Then schedule a job:
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cpu-intensive-task",
    "payload": {"data": "process_me"},
    "queue": "default"
  }'
```

**Verify:** Worker logs show `execution_mode=thread_pool`

---

## Phase 4: Capabilities & Routing

### Test 4.1: Worker with Capabilities

```bash
# Start worker with specific capabilities
python -c "
from worker.runner import Worker
import asyncio

worker = Worker(
    queue='default',
    capabilities={'network', 'cpu'},
    concurrency=2
)
asyncio.run(worker.run())
"
```

### Test 4.2: Job Requiring Capabilities

```sql
-- Create job definition requiring capabilities
INSERT INTO job_definitions (
    name, handler_ref, execution_mode, timeout_s,
    max_attempts, backoff_policy, input_schema,
    resource_profile, capabilities, visibility_timeout_s, version
) VALUES (
    'gpu-task',
    'handlers.gpu:process_model',
    'python_async',
    600,
    3,
    '{}',
    '{}',
    '{}',
    '["gpu", "network"]',  -- JSON array
    300,
    1
);
```

### Test 4.3: Capability Mismatch

```bash
# Schedule job requiring 'gpu' capability
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gpu-task",
    "payload": {},
    "queue": "default"
  }'
```

**Expected:** Worker logs show:
```
WARNING - Worker xxx rejected job yyy: missing capabilities. 
Required: ['gpu', 'network'], Available: {'network', 'cpu'}
```

**Verify:** Job is failed with `CapabilityError`

---

## Phase 5: Leases & Heartbeats

### Test 5.1: Verify Lease on Acquisition

```sql
-- Schedule a job
-- Then check lease_expires_at is set when worker acquires it
SELECT id, state, locked_by, locked_at, lease_expires_at
FROM jobs
WHERE state = 'RUNNING';
```

**Expected:** `lease_expires_at` is set to `now + visibility_timeout_s`

### Test 5.2: Test Heartbeat

1. Schedule a long-running job (simulate with sleep in handler)
2. Monitor database:

```sql
-- Watch lease_expires_at being extended
SELECT id, lease_expires_at, updated_at
FROM jobs
WHERE state = 'RUNNING'
ORDER BY updated_at DESC;
```

**Expected:** `lease_expires_at` updates every 30 seconds (heartbeat interval)

### Test 5.3: Test Lease Expiration (Manual)

```sql
-- Manually expire a lease (simulate worker crash)
UPDATE jobs
SET lease_expires_at = NOW() - INTERVAL '1 minute'
WHERE state = 'RUNNING'
LIMIT 1;
```

**Note:** Reclaim use case would pick this up (when implemented)

---

## Phase 6: Concurrency & Backpressure

### Test 6.1: Test Concurrency Limit

```bash
# Schedule 10 jobs quickly
for i in {1..10}; do
  curl -X POST "http://localhost:8000/jobs" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"process-image\",
      \"payload\": {\"image_id\": \"img-$i\"},
      \"queue\": \"default\"
    }" &
done
wait
```

**Observe Worker Logs:**
- First 4 jobs start immediately (concurrency=4)
- Remaining jobs wait for semaphore
- Jobs complete and new ones start

### Test 6.2: Verify Backpressure

```bash
# Monitor worker stats
# Worker should stop acquiring when at capacity
```

**Expected:** Worker logs show it's waiting when `len(running_tasks) >= concurrency`

---

## Phase 7: Retries & Error Handling

### Test 7.1: Test Job Failure

Create a handler that fails:

```python
# handlers/failing.py
async def failing_task(payload: dict):
    raise ValueError("Intentional failure")
```

Add to `handlers/__init__.py`:
```python
from .failing import failing_task
HANDLERS["failing-task"] = failing_task
```

Schedule job:
```bash
curl -X POST "http://localhost:8000/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "failing-task",
    "payload": {},
    "queue": "default",
    "max_attempts": 3
  }'
```

**Expected:**
1. Job fails on first attempt
2. State changes to `SCHEDULED`
3. `next_run_at` is set based on retry policy
4. Job retries after delay
5. After 3 attempts, state becomes `DEAD`

### Test 7.2: Verify Retry Policy

```sql
-- Check retry attempts
SELECT 
    j.id,
    j.name,
    j.state,
    j.attempts,
    j.max_attempts,
    j.next_run_at,
    ja.attempt_number,
    ja.success,
    ja.error_message
FROM jobs j
LEFT JOIN job_attempts ja ON j.id = ja.job_id
WHERE j.name = 'failing-task'
ORDER BY ja.attempt_number;
```

**Expected:** Multiple attempts recorded in `job_attempts` table

### Test 7.3: Test Timeout

Create a long-running handler:

```python
# handlers/slow.py
import asyncio

async def slow_task(payload: dict):
    await asyncio.sleep(400)  # Exceeds default 300s timeout
```

**Expected:** Job fails with `TimeoutError` after 300 seconds

---

## Phase 8: Automation Rules

### Test 8.1: Create Automation Rule

```bash
curl -X POST "http://localhost:8000/automation-rules" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Report",
    "description": "Generate daily report",
    "tenant_id": "tenant-1",
    "enabled": true,
    "trigger_type": "CRON",
    "trigger_config": {
      "schedule": "0 9 * * *"
    },
    "conditions": [
      {
        "field": "tenant_id",
        "operator": "eq",
        "value": "tenant-1"
      }
    ],
    "actions": [
      {
        "name": "generate-report",
        "queue": "default",
        "payload": {
          "report_type": "daily"
        }
      }
    ],
    "created_by": "admin"
  }'
```

### Test 8.2: List Automation Rules

```bash
curl "http://localhost:8000/automation-rules?tenant_id=tenant-1"
```

### Test 8.3: Test Rule Execution

(Requires automation engine to be running - see automation_engine.py)

---

## Integration Testing Checklist

### ✅ Core Functionality
- [ ] Schedule job via API
- [ ] Worker acquires and executes job
- [ ] Job state transitions correctly
- [ ] Job attempts are recorded

### ✅ Registry & Executors
- [ ] Plugin registry resolves handlers
- [ ] DB registry loads definitions
- [ ] Hybrid registry (plugin + DB) works
- [ ] Python async executor works
- [ ] Thread pool executor works (if implemented)
- [ ] HTTP executor works (if implemented)

### ✅ Advanced Features
- [ ] Capability checking rejects incompatible jobs
- [ ] Leases are set on acquisition
- [ ] Heartbeats extend leases
- [ ] Concurrency limit enforced
- [ ] Backpressure works (stops acquiring at limit)

### ✅ Error Handling
- [ ] Failed jobs retry according to policy
- [ ] Jobs become DEAD after max attempts
- [ ] Timeouts are enforced
- [ ] Errors are logged and recorded

### ✅ Multi-Worker
- [ ] Multiple workers can run simultaneously
- [ ] Jobs are distributed across workers
- [ ] No duplicate execution (row-level locking)

---

## Debugging Tips

### Check Database State

```sql
-- See all jobs
SELECT id, name, state, queue, attempts, created_at, updated_at
FROM jobs
ORDER BY created_at DESC
LIMIT 10;

-- See running jobs with leases
SELECT id, name, locked_by, lease_expires_at, 
       NOW() - lease_expires_at as lease_age
FROM jobs
WHERE state = 'RUNNING';

-- See job attempts
SELECT ja.*, j.name, j.state
FROM job_attempts ja
JOIN jobs j ON ja.job_id = j.id
ORDER BY ja.started_at DESC
LIMIT 10;
```

### Enable Debug Logging

```python
# In worker/runner.py or main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Individual Components

```python
# Test job registry
from adapters.outbound.registry.initializers import create_registry_from_handlers
from handlers import HANDLERS

registry = create_registry_from_handlers(HANDLERS)
definition = await registry.get_definition("send-email")
handler = await registry.get_handler("send-email")
```

---

## Performance Testing

### Load Test

```bash
# Schedule 100 jobs
for i in {1..100}; do
  curl -X POST "http://localhost:8000/jobs" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"process-image\",
      \"payload\": {\"image_id\": \"img-$i\"},
      \"queue\": \"default\"
    }" &
done
```

**Monitor:**
- Worker throughput (jobs/second)
- Database connection pool
- Memory usage

---

## Next Steps

1. **Add Unit Tests**: Create `tests/` directory with pytest
2. **Add Integration Tests**: Test full workflows
3. **Add E2E Tests**: Test complete user scenarios
4. **Add Monitoring**: Prometheus metrics, Grafana dashboards
5. **Add CI/CD**: Automated testing pipeline

---

## Automated Unit Tests (Quick Start)

We include minimal async unit tests using in-memory fakes that exercise:
- success and failure paths
- retry behavior
- acquisition with queue/tenant limits
- automation rule job creation

Run:

```bash
pip install pytest pytest-asyncio
pytest -q
```

---

## Integration Tests (Database-backed)

We include optional integration tests that execute against a real Postgres DB.
They mirror the SQL steps used in manual demos:

- queue + tenant setup
- scheduling + acquisition + completion
- queue and tenant concurrency limits
- automation rule triggers

Run:

```bash
# PowerShell
$env:TASKFLOW_DATABASE_URL="postgresql+asyncpg://postgres:root@localhost:5432/taskflow"
python -m pytest -q tests/integration/test_db_workflows.py
```

---

## Troubleshooting

### Migration Errors

```bash
# Check current migration
python -m alembic current

# Rollback if needed
python -m alembic downgrade -1

# Check migration history
python -m alembic history
```

### Database Connection Issues

```bash
# Test connection
psql -U postgres -d taskflow -c "SELECT 1;"

# Check .env file
cat .env | grep DATABASE_URL
```

### Worker Not Processing Jobs

1. Check worker is running
2. Check queue name matches
3. Check job state is PENDING or SCHEDULED
4. Check `next_run_at` is in the past
5. Check database connection

---

## Summary

This testing guide covers:
- ✅ Basic job scheduling and execution
- ✅ Worker processing with multiple executors
- ✅ Job registry (plugin + DB hybrid)
- ✅ Capability-based routing
- ✅ Lease management and heartbeats
- ✅ Concurrency control
- ✅ Retries and error handling
- ✅ Automation rules

Follow these steps systematically to verify all features work correctly!
