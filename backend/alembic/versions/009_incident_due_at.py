"""add optional incident due_at for SLA-style targets

Revision ID: 009_incident_due_at
Revises: 008_incident_history
Create Date: 2026-05-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_incident_due_at"
down_revision: Union[str, None] = "008_incident_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("due_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_incidents_due_at"), "incidents", ["due_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_incidents_due_at"), table_name="incidents")
    op.drop_column("incidents", "due_at")
