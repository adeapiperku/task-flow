import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine():
    """
    Dispose the SQLAlchemy engine at the end of the test session.
    """
    yield
    from adapters.outbound.db.base import engine
    await engine.dispose()
