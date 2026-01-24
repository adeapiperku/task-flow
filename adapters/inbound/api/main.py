# adapters/inbound/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.inbound.api.error_handlers import register_error_handlers
from adapters.inbound.api.routers import jobs, automation_rules, events
from adapters.outbound.db.uow_sqlalchemy import SqlAlchemyUnitOfWork
from domain.ports.automation_rule_repository import AutomationRuleRepository

app = FastAPI(
    title="TaskFlow API",
    description="TaskFlow - Job Automation Engine",
    version="0.1.0",
)

# CORS middleware should be one of the first middlewares to be added
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Then register error handlers and other middleware
register_error_handlers(app)

# Then include routers
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(automation_rules.router)
app.include_router(events.router)
