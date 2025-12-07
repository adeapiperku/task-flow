# adapters/inbound/api/routers/jobs.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.inbound.api.schemas.job_response import JobResponse
from application.dto.schedule_job_command import ScheduleJobCommand
from application.use_cases.schedule_job import ScheduleJobUseCase
from application.use_cases.get_job_by_id import GetJobByIdUseCase

router = APIRouter()


def get_schedule_job_use_case() -> ScheduleJobUseCase:
    return ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)


def get_get_job_by_id_use_case() -> GetJobByIdUseCase:
    return GetJobByIdUseCase(uow_factory=SqlAlchemyUnitOfWork)


@router.post("", response_model=JobResponse, status_code=201)
async def schedule_job(
    cmd: ScheduleJobCommand,
    use_case: ScheduleJobUseCase = Depends(get_schedule_job_use_case),
):
    job = await use_case.execute(cmd)
    return JobResponse.from_domain(job)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    use_case: GetJobByIdUseCase = Depends(get_get_job_by_id_use_case),
):
    job = await use_case.execute(job_id)
    return JobResponse.from_domain(job)
