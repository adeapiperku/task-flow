# adapters/outbound/db/mappers/job_definition_mapper.py
from __future__ import annotations

from adapters.outbound.db.models import JobDefinitionOrm
from domain.models.job_definition import JobDefinition


class JobDefinitionMapper:
    """Mapper between JobDefinitionOrm and domain JobDefinition."""

    @staticmethod
    def to_domain(orm: JobDefinitionOrm) -> JobDefinition:
        """Convert ORM model to domain model."""
        return JobDefinition(
            name=orm.name,
            handler_ref=orm.handler_ref,
            execution_mode=orm.execution_mode,
            timeout_s=orm.timeout_s,
            max_attempts=orm.max_attempts,
            backoff_policy=orm.backoff_policy or {},
            input_schema=orm.input_schema or {},
            resource_profile=orm.resource_profile or {},
            capabilities=orm.capabilities or [],
            visibility_timeout_s=getattr(orm, 'visibility_timeout_s', 300),  # Default 5 minutes
            version=orm.version,
        )

    @staticmethod
    def to_orm(definition: JobDefinition) -> JobDefinitionOrm:
        """Convert domain model to ORM model."""
        return JobDefinitionOrm(
            name=definition.name,
            handler_ref=definition.handler_ref,
            execution_mode=definition.execution_mode,
            timeout_s=definition.timeout_s,
            max_attempts=definition.max_attempts,
            backoff_policy=definition.backoff_policy,
            input_schema=definition.input_schema,
            resource_profile=definition.resource_profile,
            capabilities=definition.capabilities,
            visibility_timeout_s=definition.visibility_timeout_s,
            version=definition.version,
        )


