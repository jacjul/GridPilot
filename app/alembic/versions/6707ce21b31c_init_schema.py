"""init schema

Revision ID: 6707ce21b31c
Revises:
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op

from app.db.database import Base
from app.models import battery  # noqa: F401
from app.models import electric_vehicle  # noqa: F401
from app.models import optimization  # noqa: F401
from app.models import photovoltaik  # noqa: F401
from app.models import price_electricity  # noqa: F401
from app.models import PV_forecast  # noqa: F401
from app.models import token  # noqa: F401
from app.models import user  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "6707ce21b31c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
