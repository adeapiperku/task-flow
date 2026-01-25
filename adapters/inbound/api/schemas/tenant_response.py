from pydantic import BaseModel
from datetime import datetime

class TenantResponse(BaseModel):
    id: str
    name: str
    max_running_jobs: int
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
