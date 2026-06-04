"""Align starter billing_settings price with plan catalog (7900 cents).

Revision ID: 011_starter_billing_defaults
Revises: 010_refresh_tokens
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa

revision = "011_starter_billing_defaults"
down_revision = "010_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "billing_settings",
        "monthly_price_cents",
        server_default=sa.text("7900"),
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.execute(
        """
        UPDATE billing_settings
        SET monthly_price_cents = 7900
        WHERE plan_key = 'starter' AND monthly_price_cents = 14900
        """
    )


def downgrade() -> None:
    op.alter_column(
        "billing_settings",
        "monthly_price_cents",
        server_default=sa.text("14900"),
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
