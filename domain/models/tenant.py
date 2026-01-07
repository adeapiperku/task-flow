from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Tenant:
    """
    Domain model for a tenant.
    """

    id: str
    max_running_jobs: int
    weight: int
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def new(
        *,
        id: str,
        max_running_jobs: int = 5,
        weight: int = 1,
    ) -> "Tenant":
        now = datetime.utcnow()
        return Tenant(
            id=id,
            max_running_jobs=max_running_jobs,
            weight=weight,
            created_at=now,
            updated_at=now,
        )

    def update_limits(
        self,
        *,
        max_running_jobs: int | None = None,
        weight: int | None = None,
    ) -> "Tenant":
        data: dict[str, Any] = self.__dict__.copy()
        if max_running_jobs is not None:
            data["max_running_jobs"] = max_running_jobs
        if weight is not None:
            data["weight"] = weight
        data["updated_at"] = datetime.utcnow()
        return Tenant(**data)
