# Tenants and Queues

This document explains the tenant and queue system, their relationships, and how they manage job execution.

## Overview

- **Tenants** provide multi-tenancy isolation
- **Queues** organize jobs and control their execution
- Together they enable fine-grained control over resource allocation

## Tenants

### Core Properties
- `id`: Unique identifier (string)
- `max_running_jobs`: Maximum concurrent jobs (default: 5)
- `weight`: Priority weight for job acquisition (default: 1)
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last update

### Key Behaviors
- Enforces maximum concurrent jobs per tenant
- Used for resource isolation between customers/teams
- Weight affects job acquisition priority (higher = higher priority)

## Queues

### Core Properties
- `name`: Unique identifier (string)
- `max_concurrency`: Maximum concurrent jobs (default: 10)
- `priority`: Priority for job selection (default: 0, higher = higher priority)
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last update

### Key Behaviors
- Jobs are assigned to queues for organization
- Enforces maximum concurrency per queue
- Priority affects job selection within the queue
- Queues can be enabled/disabled

## Job Acquisition and Execution

### Selection Criteria
Jobs are selected based on:
1. Queue priority (higher first)
2. Job priority (higher first)
3. Creation time (older first)
4. Tenant weight (if multiple tenants have jobs)

### Concurrency Limits
- **Queue-level**: `max_concurrency` limits jobs per queue
- **Tenant-level**: `max_running_jobs` limits jobs per tenant
- System enforces both limits during job acquisition

### Fairness
- Round-robin between tenants with equal priority
- Weighted distribution based on tenant weights
- Prevents starvation of lower-priority queues

## Database Schema

### Tenants Table
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    max_running_jobs INTEGER NOT NULL,
    weight INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### Queues Table
```sql
CREATE TABLE queues (
    name VARCHAR(255) PRIMARY KEY,
    max_concurrency INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

## Error Conditions

### Queue Full
- When queue reaches `max_concurrency`
- Job remains in queue until capacity is available

### Tenant Limit Reached
- When tenant reaches `max_running_jobs`
- Other jobs from the same tenant wait
- Jobs from other tenants can still be processed

## Best Practices

### Tenant Configuration
- Set appropriate `max_running_jobs` based on tenant needs
- Use weights to prioritize important tenants
- Monitor tenant resource usage

### Queue Configuration
- Organize queues by job type/priority
- Set realistic concurrency limits
- Use priorities to ensure critical jobs run first

## Monitoring

Key metrics to track:
- Queue depths
- Job wait times
- Concurrency usage per queue/tenant
- Rejection rates

## Example Scenarios

### High-Priority Processing
```python
# High-priority queue for time-sensitive jobs
await queue_repository.save(Queue.new(
    name="high_priority",
    max_concurrency=5,
    priority=100
))

# Tenant with higher weight gets more resources
tenant = Tenant.new(
    id="premium_customer",
    max_running_jobs=20,
    weight=10
)
```

### Resource-Limited Tenant
```python
# Tenant with strict resource limits
await tenant_repository.save(Tenant.new(
    id="free_tier",
    max_running_jobs=2,
    weight=1
))
```
