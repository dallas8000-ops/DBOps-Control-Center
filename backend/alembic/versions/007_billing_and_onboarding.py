"""add billing settings and onboarding events

Revision ID: 007_billing_onboarding
Revises: 006_sched_delivery_targets
Create Date: 2026-05-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_billing_onboarding"
down_revision: Union[str, None] = "006_sched_delivery_targets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_key", sa.String(length=80), nullable=False, server_default=sa.text("'starter'")),
        sa.Column("billing_status", sa.String(length=40), nullable=False, server_default=sa.text("'trialing'")),
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False, server_default=sa.text("14900")),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("max_schedules", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("stripe_customer_id", sa.String(length=120), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "onboarding_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_events_actor_user_id"), "onboarding_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_onboarding_events_created_at"), "onboarding_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_onboarding_events_event_key"), "onboarding_events", ["event_key"], unique=True)
    op.execute(
        sa.text(
            """
            INSERT INTO billing_settings (
                id, plan_key, billing_status, monthly_price_cents, max_users, max_schedules
            ) VALUES (1, 'starter', 'trialing', 14900, 10, 10)
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_onboarding_events_event_key"), table_name="onboarding_events")
    op.drop_index(op.f("ix_onboarding_events_created_at"), table_name="onboarding_events")
    op.drop_index(op.f("ix_onboarding_events_actor_user_id"), table_name="onboarding_events")
    op.drop_table("onboarding_events")
    op.drop_table("billing_settings")
