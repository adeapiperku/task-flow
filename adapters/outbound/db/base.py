# task_flow/adapters/outbound/db/base.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.py."""
    pass


def _create_engine(database_url: str, *, use_null_pool: bool = False):
    from sqlalchemy.pool import NullPool
    return create_async_engine(
        database_url,
        echo=False,           # set True during debugging
        pool_pre_ping=True,
        poolclass=NullPool if use_null_pool else None,
    )


engine = _create_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def reset_engine(
    database_url: str | None = None,
    *,
    use_null_pool: bool = False,
) -> None:
    """
    Recreate the async engine and sessionmaker.

    This is used by integration tests to bind connections to the
    currently running event loop.
    """
    global engine, AsyncSessionLocal
    try:
        await engine.dispose()
    except Exception:
        pass

    url = database_url or settings.database_url
    engine = _create_engine(url, use_null_pool=use_null_pool)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
