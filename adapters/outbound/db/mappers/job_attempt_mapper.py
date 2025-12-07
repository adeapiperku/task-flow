# adapters/outbound/db/mappers/job_attempt_mapper.py
from __future__ import annotations

from adapters.outbound.db.models import JobAttemptOrm
from domain.models.job_attempt import JobAttempt


class JobAttemptMapper:
    @staticmethod
    def to_orm(attempt: JobAttempt) -> JobAttemptOrm:
        return JobAttemptOrm(
            id=attempt.id,
            job_id=attempt.job_id,
            attempt_number=attempt.attempt_number,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
            success=attempt.success,
            error_type=attempt.error_type,
            error_message=attempt.error_message,
            worker_id=attempt.worker_id,
        )

    @staticmethod
    def to_domain(orm: JobAttemptOrm) -> JobAttempt:
        return JobAttempt(
            id=orm.id,
            job_id=orm.job_id,
            attempt_number=orm.attempt_number,
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            success=orm.success,
            error_type=orm.error_type,
            error_message=orm.error_message,
            worker_id=orm.worker_id,
        )
