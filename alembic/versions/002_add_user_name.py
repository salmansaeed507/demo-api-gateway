"""Add name to users.

Revision ID: 002
Revises: 001
Create Date: 2026-09-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("users", "name", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "name")
