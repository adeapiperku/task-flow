# adapters/outbound/db/mappers/job_mapper.py
from __future__ import annotations

from adapters.outbound.db.models import JobOrm
from domain.models.job import Job, JobState


class JobMapper:
    """
    Dedicated mapper between Job (domain) and JobOrm (DB layer).
    Centralized translation logic to keep adapters thin and clean.
    """

    @staticmethod
    def to_orm(job: Job) -> JobOrm:
        return JobOrm(
            id=job.id,
            queue=job.queue,
            name=job.name,
            tenant_id=job.tenant_id,
            payload=job.payload,
            state=job.state.value,
            priority=job.priority,
            created_at=job.created_at,
            updated_at=job.updated_at,
            scheduled_at=job.scheduled_at,
            next_run_at=job.next_run_at,
            last_run_at=job.last_run_at,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            archived=job.archived,
            locked_by=job.locked_by,
            locked_at=job.locked_at,
        )

    @staticmethod
    def to_domain(orm: JobOrm) -> Job:
        return Job(
            id=orm.id,
            queue=orm.queue,
            name=orm.name,
            tenant_id=orm.tenant_id,
            payload=dict(orm.payload or {}),
            state=JobState(orm.state),
            priority=orm.priority,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            scheduled_at=orm.scheduled_at,
            next_run_at=orm.next_run_at,
            last_run_at=orm.last_run_at,
            attempts=orm.attempts,
            max_attempts=orm.max_attempts,
            archived=orm.archived,
            locked_by=orm.locked_by,
            locked_at=orm.locked_at,
        )
