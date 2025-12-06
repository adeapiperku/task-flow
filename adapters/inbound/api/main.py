# adapters/inbound/api/main.py
from __future__ import annotations

from fastapi import FastAPI, Depends

from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from adapters.inbound.api.schemas import JobResponse
from adapters.inbound.api.error_handlers import register_error_handlers

from application.dto.schedule_job_command import ScheduleJobCommand
from application.use_cases.schedule_job import ScheduleJobUseCase


app = FastAPI(title="task-flow")
register_error_handlers(app)


def get_schedule_job_use_case() -> ScheduleJobUseCase:
    return ScheduleJobUseCase(uow_factory=SqlAlchemyUnitOfWork)


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def schedule_job(
    cmd: ScheduleJobCommand,
    use_case: ScheduleJobUseCase = Depends(get_schedule_job_use_case),
):
    job = await use_case.execute(cmd)
    return JobResponse.from_domain(job)
