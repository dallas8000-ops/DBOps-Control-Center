"""add user admin audit logs

Revision ID: 004_user_admin_audit_logs
Revises: 003_users_active
Create Date: 2026-05-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_user_admin_audit_logs"
down_revision: Union[str, None] = "003_users_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("target_email", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_admin_audit_logs_id"), "user_admin_audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_user_admin_audit_logs_actor_user_id"), "user_admin_audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_user_admin_audit_logs_target_user_id"), "user_admin_audit_logs", ["target_user_id"], unique=False)
    op.create_index(op.f("ix_user_admin_audit_logs_action"), "user_admin_audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_user_admin_audit_logs_created_at"), "user_admin_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_admin_audit_logs_created_at"), table_name="user_admin_audit_logs")
    op.drop_index(op.f("ix_user_admin_audit_logs_action"), table_name="user_admin_audit_logs")
    op.drop_index(op.f("ix_user_admin_audit_logs_target_user_id"), table_name="user_admin_audit_logs")
    op.drop_index(op.f("ix_user_admin_audit_logs_actor_user_id"), table_name="user_admin_audit_logs")
    op.drop_index(op.f("ix_user_admin_audit_logs_id"), table_name="user_admin_audit_logs")
    op.drop_table("user_admin_audit_logs")