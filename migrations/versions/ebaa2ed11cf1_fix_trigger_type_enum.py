"""fix_trigger_type_enum

Revision ID: ebaa2ed11cf1
Revises: a7ada65b6c50
Create Date: 2026-01-13 22:08:06.270774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebaa2ed11cf1'
down_revision: Union[str, Sequence[str], None] = 'a7ada65b6c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
