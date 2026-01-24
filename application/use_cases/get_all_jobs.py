from typing import List
from uuid import UUID

from application.uow import UnitOfWork, UnitOfWorkFactory
from domain.models.job import Job
from domain.ports.job_repository import JobRepository


class GetAllJobsUseCase:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self) -> List[Job]:
        async with self.uow_factory() as uow:
            # Use job_repo instead of jobs
            job_repo = uow.job_repo
            if job_repo is None:
                raise ValueError("Job repository not initialized")
            return await job_repo.get_all()