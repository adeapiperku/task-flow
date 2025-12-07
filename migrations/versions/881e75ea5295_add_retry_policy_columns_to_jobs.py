"""add retry policy columns to jobs

Revision ID: 881e75ea5295
Revises: ad571f39a147
Create Date: 2025-12-07 18:24:45.175778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '881e75ea5295'
down_revision: Union[str, Sequence[str], None] = 'ad571f39a147'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "jobs",
        sa.Column(
            "retry_strategy",
            sa.String(length=32),
            nullable=False,
            server_default="EXPONENTIAL",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "retry_base_delay_seconds",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jobs", "retry_base_delay_seconds")
    op.drop_column("jobs", "retry_strategy")
