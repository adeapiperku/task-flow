# task_flow/adapters/outbound/db/base.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.py."""
    pass


engine = create_async_engine(
    settings.database_url,
    echo=False,           # set True during debugging
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
