from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, create_engine

# Import your Base and models so Alembic sees them
from adapters.outbound.db.base import Base
from adapters.outbound.db import models  # noqa: F401
from config.settings import settings

# Alembic Config object
config = context.config

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the metadata Alembic will generate migrations from
target_metadata = Base.metadata


def get_sync_url() -> str:
    """Alembic uses synchronous engines, remove +asyncpg."""
    url = settings.database_url
    return url.replace("+asyncpg", "")


def run_migrations_offline():
    """Run migrations in offline mode."""
    url = get_sync_url()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in online mode."""
    url = get_sync_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
