from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class JobDefinition:
    """
    Defines a job type (aka "task") that workers can execute.
    This is NOT a job run. It's the template/contract for a job name.
    """
    name: str                     # e.g. "email.send"
    handler_ref: str              # e.g. "taskflow_jobs.email:send_email"
    execution_mode: str           # e.g. "python_async" (later: "http", "container", ...)
    timeout_s: int
    max_attempts: int
    backoff_policy: Mapping[str, Any]   # json-like dict
    input_schema: Mapping[str, Any]     # jsonschema or your own schema
    resource_profile: Mapping[str, Any] # e.g. {"cpu":1,"mem_mb":256}
    capabilities: list[str]            # e.g. ["network", "smtp"]
    version: int
