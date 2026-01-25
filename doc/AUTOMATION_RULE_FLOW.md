# Automation Rule End-to-End Flow

This document explains how automation rules are processed, from creation to execution.
It focuses on the rule evaluation flow and component interactions.

## High-level flow

1) Rule is created/updated with conditions and actions
2) Job completion/failure triggers rule evaluation
3) Conditions are evaluated against job/context
4) If conditions match, actions are executed
5) Action results are processed and logged

## Core classes and responsibilities

### `AutomationEngine` (`domain/services/automation_engine.py`)
Responsibilities:
- Main entry point for rule processing
- Coordinates condition evaluation and action execution
- Manages rule execution context

Key methods:
- `process_job_event(job, event_type)`: Processes job events through matching rules
- `evaluate_rule(rule, context)`: Evaluates a single rule's conditions
- `execute_actions(rule, context)`: Executes all actions for a rule

### `AutomationRule` (`domain/models/automation_rule.py`)
Responsibilities:
- Defines rule structure and behavior
- Holds conditions and actions
- Manages rule state and metadata

Key fields:
- `name`, `description`
- `event_types`: List of events that trigger this rule
- `conditions`: Conditions that must be met
- `actions`: Actions to execute when conditions are met
- `enabled`: Whether the rule is active
- `priority`: Rule execution order

### `Condition` (`domain/models/constraints.py`)
Responsibilities:
- Defines condition logic and evaluation
- Supports various condition types (job attributes, custom logic, etc.)

Key methods:
- `evaluate(context)`: Returns True if condition is met
- `to_dict()`: Serializes condition for storage

### `Action` (`domain/ports/executor.py`)
Responsibilities:
- Defines action interface
- Handles action execution and results

Key methods:
- `execute(context)`: Performs the action
- `validate(context)`: Validates action can be executed

## Method call order (typical execution)

1) Job completes/fails
2) `AutomationEngine.process_job_event(job, event_type)`
3) `AutomationRuleRepository.get_rules_for_event(event_type)`
4) For each matching rule:
   1) `AutomationEngine.evaluate_rule(rule, context)`
   2) If conditions pass: `AutomationEngine.execute_actions(rule, context)`
   3) `Action.execute(context)` for each action

## Rule Evaluation

- Rules are processed in priority order (lower numbers first)
- All conditions must evaluate to True for actions to execute
- Conditions can check:
  - Job attributes (status, queue, metadata)
  - Execution context (time, retry count, etc.)
  - Custom logic via plugins

## Action Execution

- Actions execute in defined order
- Supported action types:
  - Create new jobs
  - Update job attributes
  - Send notifications
  - Trigger webhooks
  - Execute custom code

## Error Handling

- Failed condition evaluations are logged but don't stop processing
- Failed actions are logged and processing continues with next action
- Action execution timeouts prevent long-running actions

## Observability (logs)

Key log points:
- Rule evaluation start/end
- Condition evaluation results
- Action execution start/end
- Execution errors and warnings
- Performance metrics (evaluation time, action duration)

## Example Rule Definition

```yaml
name: "Notify on Job Failure"
description: "Send notification when a job fails"
event_types: ["job_failed"]
enabled: true
priority: 1
conditions:
  - type: "job_status"
    operator: "equals"
    value: "failed"
  - type: "retry_count"
    operator: "greater_than"
    value: 3
actions:
  - type: "notification"
    channel: "email"
    recipients: ["team@example.com"]
    message: "Job {{job_id}} failed after {{retry_count}} attempts"
  - type: "webhook"
    url: "https://alerts.example.com/notify"
    method: "POST"
    body: {"job_id": "{{job_id}}", "status": "failed"}
```
