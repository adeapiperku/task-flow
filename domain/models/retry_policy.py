# domain/models/retry_policy.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class RetryStrategy(str, Enum):
    FIXED = "FIXED"
    EXPONENTIAL = "EXPONENTIAL"


@dataclass(frozen=True)
class RetryPolicy:
    """
    Retry behaviour for a job.

    This is a persisted, per-job policy:
    - strategy: FIXED or EXPONENTIAL
    - base_delay_seconds: starting delay in seconds

    The maximum number of attempts is still stored on the Job (max_attempts).
    """

    strategy: RetryStrategy
    base_delay_seconds: int

    def compute_next_run_at(
        self,
        *,
        attempts_after_increment: int,
        max_attempts: int,
        now: datetime,
    ) -> datetime | None:
        """
        Return the timestamp for the next attempt, or None if the job
        should not be retried anymore and must become DEAD.
        """
        if attempts_after_increment >= max_attempts:
            # exceeded retry budget
            return None

        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay_seconds
        else:
            # exponential backoff: base, 2*base, 4*base, ...
            delay = self.base_delay_seconds * (2 ** (attempts_after_increment - 1))

        return now + timedelta(seconds=delay)
