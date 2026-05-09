"""add report schedule delivery targets

Revision ID: 006_report_schedule_delivery_targets
Revises: 005_report_schedules
Create Date: 2026-05-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_report_schedule_delivery_targets"
down_revision: Union[str, None] = "005_report_schedules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "report_schedules",
        sa.Column("delivery_kind", sa.String(length=20), nullable=False, server_default="none"),
    )
    op.add_column(
        "report_schedules",
        sa.Column("delivery_target", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "report_schedules",
        sa.Column("notify_on_success", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "report_schedules",
        sa.Column("notify_on_failure", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_check_constraint(
        "ck_report_schedules_delivery_kind",
        "report_schedules",
        "delivery_kind in ('none', 'email', 'webhook')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_report_schedules_delivery_kind", "report_schedules", type_="check")
    op.drop_column("report_schedules", "notify_on_failure")
    op.drop_column("report_schedules", "notify_on_success")
    op.drop_column("report_schedules", "delivery_target")
    op.drop_column("report_schedules", "delivery_kind")
