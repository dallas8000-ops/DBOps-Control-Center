"""report execution audit table

Revision ID: 002_report_logs
Revises: 001_initial
Create Date: 2026-05-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_report_logs"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_execution_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_key", sa.String(length=120), nullable=False),
        sa.Column("params_json", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_execution_logs_id"), "report_execution_logs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_execution_logs_id"), table_name="report_execution_logs")
    op.drop_table("report_execution_logs")
