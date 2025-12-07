# adapters/inbound/api/main.py
from fastapi import FastAPI
from adapters.inbound.api.error_handlers import register_error_handlers
from adapters.inbound.api.routers import jobs

app = FastAPI(title="task-flow")

register_error_handlers(app)

# All job-related endpoints are in jobs.router
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
