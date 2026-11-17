"""initial tables

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_integration_settings_key", "integration_settings", ["key"], unique=True)
    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("operation", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_operation_logs_operation", "operation_logs", ["operation"])
    op.create_index("ix_operation_logs_status", "operation_logs", ["status"])
    op.create_index("ix_operation_logs_created_at", "operation_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_operation_logs_created_at", table_name="operation_logs")
    op.drop_index("ix_operation_logs_status", table_name="operation_logs")
    op.drop_index("ix_operation_logs_operation", table_name="operation_logs")
    op.drop_table("operation_logs")
    op.drop_index("ix_integration_settings_key", table_name="integration_settings")
    op.drop_table("integration_settings")
