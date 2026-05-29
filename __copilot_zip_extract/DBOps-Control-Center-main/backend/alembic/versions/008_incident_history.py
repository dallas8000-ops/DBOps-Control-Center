"""add incident history audit trail

Revision ID: 008_incident_history
Revises: 007_billing_onboarding
Create Date: 2026-05-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_incident_history"
down_revision: Union[str, None] = "007_billing_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incident_history_id"), "incident_history", ["id"], unique=False)
    op.create_index(op.f("ix_incident_history_incident_id"), "incident_history", ["incident_id"], unique=False)
    op.create_index(op.f("ix_incident_history_actor_user_id"), "incident_history", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_incident_history_action"), "incident_history", ["action"], unique=False)
    op.create_index(op.f("ix_incident_history_created_at"), "incident_history", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_incident_history_created_at"), table_name="incident_history")
    op.drop_index(op.f("ix_incident_history_action"), table_name="incident_history")
    op.drop_index(op.f("ix_incident_history_actor_user_id"), table_name="incident_history")
    op.drop_index(op.f("ix_incident_history_incident_id"), table_name="incident_history")
    op.drop_index(op.f("ix_incident_history_id"), table_name="incident_history")
    op.drop_table("incident_history")
