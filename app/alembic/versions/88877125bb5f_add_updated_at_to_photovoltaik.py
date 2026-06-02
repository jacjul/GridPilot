"""add_updated_at_to_photovoltaik

Revision ID: 88877125bb5f
Revises: 6707ce21b31c
Create Date: 2026-05-22 11:36:58.569594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '88877125bb5f'
down_revision: Union[str, Sequence[str], None] = '6707ce21b31c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("photovoltaik")}

    if "updated_at" not in columns:
        op.add_column(
            "photovoltaik",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("photovoltaik")}

    if "updated_at" in columns:
        op.drop_column("photovoltaik", "updated_at")
