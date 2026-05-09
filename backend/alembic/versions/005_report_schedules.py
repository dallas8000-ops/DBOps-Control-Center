"""add report schedules

Revision ID: 005_report_schedules
Revises: 004_user_admin_audit_logs
Create Date: 2026-05-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_report_schedules"
down_revision: Union[str, None] = "004_user_admin_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("report_key", sa.String(length=120), nullable=False),
        sa.Column("params_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("cadence", sa.String(length=20), nullable=False),
        sa.Column("weekday_utc", sa.Integer(), nullable=True),
        sa.Column("run_hour_utc", sa.Integer(), nullable=False),
        sa.Column("run_minute_utc", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("next_run_at", sa.DateTime(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("cadence in ('daily', 'weekly')", name="ck_report_schedules_cadence"),
        sa.CheckConstraint("run_hour_utc >= 0 and run_hour_utc <= 23", name="ck_report_schedules_hour"),
        sa.CheckConstraint("run_minute_utc >= 0 and run_minute_utc <= 59", name="ck_report_schedules_minute"),
        sa.CheckConstraint(
            "weekday_utc is null or (weekday_utc >= 0 and weekday_utc <= 6)",
            name="ck_report_schedules_weekday",
        ),
    )
    op.create_index(op.f("ix_report_schedules_id"), "report_schedules", ["id"], unique=False)
    op.create_index(op.f("ix_report_schedules_created_by_user_id"), "report_schedules", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_report_schedules_next_run_at"), "report_schedules", ["next_run_at"], unique=False)
    op.create_index(op.f("ix_report_schedules_created_at"), "report_schedules", ["created_at"], unique=False)

    op.add_column("report_execution_logs", sa.Column("scheduled_report_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_report_execution_logs_scheduled_report_id"),
        "report_execution_logs",
        ["scheduled_report_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_report_execution_logs_scheduled_report_id_report_schedules",
        "report_execution_logs",
        "report_schedules",
        ["scheduled_report_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_report_execution_logs_scheduled_report_id_report_schedules",
        "report_execution_logs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_report_execution_logs_scheduled_report_id"), table_name="report_execution_logs")
    op.drop_column("report_execution_logs", "scheduled_report_id")

    op.drop_index(op.f("ix_report_schedules_created_at"), table_name="report_schedules")
    op.drop_index(op.f("ix_report_schedules_next_run_at"), table_name="report_schedules")
    op.drop_index(op.f("ix_report_schedules_created_by_user_id"), table_name="report_schedules")
    op.drop_index(op.f("ix_report_schedules_id"), table_name="report_schedules")
    op.drop_table("report_schedules")
