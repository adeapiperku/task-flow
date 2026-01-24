# TaskFlow End-to-End Testing (Manual Demo)

This guide describes how to test the system end to end with manual DB inserts
and with the HTTP API. It focuses on predictable results for a presentation.

Assumptions:
- Postgres is configured and migrations are applied.
- API is running from `adapters/inbound/api/main.py`.
- Worker is running from `worker/runner.py`.

## 1) Prepare the database

Create a queue and a tenant with small limits to see fairness in action.

```sql
-- queue with max 1 concurrent job
INSERT INTO queues (name, max_concurrency, active)
VALUES ('default', 1, true)
ON CONFLICT (name) DO UPDATE
SET max_concurrency = EXCLUDED.max_concurrency, active = EXCLUDED.active;

-- tenant with max 1 running job
INSERT INTO tenants (id, name, max_running_jobs, active)
VALUES ('11111111-1111-1111-1111-111111111111', 'demo-tenant', 1, true)
ON CONFLICT (id) DO UPDATE
SET max_running_jobs = EXCLUDED.max_running_jobs, active = EXCLUDED.active;
```

## 2) Start API and worker

In separate terminals:

```bash
python -m adapters.inbound.api.main
```

```bash
python -m worker.runner --queue default --concurrency 2
```

Expected:
- API starts successfully.
- Worker starts polling the `default` queue.

## 3) Register a job handler (plugin)

Ensure you have handlers registered in `handlers/__init__.py`.
Example job name: `email.send` or `image.resize`.

Expected:
- Plugin registry can resolve the handler.

## 4) Schedule a job (API path)

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "email.send",
    "payload": {"to": "demo@example.com"},
    "queue": "default",
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "priority": 0,
    "max_attempts": 2
  }'
```

Expected:
- Job is created in state PENDING.
- Worker acquires it and marks RUNNING.
- Job finishes and becomes SUCCEEDED.
- A JobAttempt row is inserted.

## 5) Verify in database

```sql
SELECT id, name, state, attempts, next_run_at, locked_by
FROM jobs
ORDER BY created_at DESC
LIMIT 5;

SELECT job_id, attempt_number, success, error_message
FROM job_attempts
ORDER BY started_at DESC
LIMIT 5;
```

Expected:
- `attempts` is 1 for the succeeded job.
- One JobAttempt row exists with success=true.

## 6) Failure + retry path (manual DB insert)

Insert a job that will fail (use a handler that raises).

```sql
INSERT INTO jobs (
  id, queue, name, tenant_id, payload, state, priority,
  created_at, updated_at, scheduled_at, next_run_at,
  attempts, max_attempts, archived,
  retry_strategy, retry_base_delay_seconds
) VALUES (
  gen_random_uuid(),
  'default',
  'email.send',
  '11111111-1111-1111-1111-111111111111',
  '{"force_fail": true}',
  'PENDING',
  0,
  NOW(), NOW(), NOW(), NOW(),
  0, 2, false,
  'FIXED', 5
);
```

Expected:
- On first failure: attempts=1, state=SCHEDULED, next_run_at ~ now+5s.
- On second failure: attempts=2, state=DEAD, next_run_at NULL.

## 7) Automation rule trigger via HTTP event

Create a rule:

```bash
curl -X POST http://localhost:8000/automation-rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo-rule",
    "description": "Create job on webhook event",
    "trigger": {"type": "WEBHOOK", "config": {"path": "webhook.demo"}},
    "conditions": [{"field": "plan", "operator": "eq", "value": "pro"}],
    "actions": [{"name": "email.send", "queue": "default", "payload": {"to": "pro@example.com"}}]
  }'
```

Trigger event:

```bash
curl -X POST http://localhost:8000/events/webhook.demo \
  -H "Content-Type: application/json" \
  -d '{"context": {"plan": "pro"}, "tenant_id": "11111111-1111-1111-1111-111111111111"}'
```

Expected:
- Event evaluates rules and inserts jobs.
- Response returns created jobs.
- Worker picks and executes them.

## 8) Fairness demo

Create two jobs for the same tenant and queue.

Expected:
- Only one runs at a time due to max_concurrency and max_running_jobs.
- Second job waits until the first completes.

## Troubleshooting checklist

- If jobs stay PENDING: confirm worker is running and queue is active.
- If jobs stay RUNNING: check leases and heartbeat interval.
- If retries never happen: check retry_strategy and retry_base_delay_seconds.
- If rules do not trigger: confirm tenant_id is provided and trigger config matches event_type.
