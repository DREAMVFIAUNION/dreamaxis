"""provider connections and dynamic model bindings

Revision ID: 0003_provider_connections
Revises: 0002_provider_knowledge_runtime
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_provider_connections"
down_revision = "0002_provider_knowledge_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider_id", sa.String(length=64), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("provider_type", sa.String(length=50), nullable=False, server_default="openai_compatible"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("model_discovery_mode", sa.String(length=32), nullable=False, server_default="auto"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="requires_config"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_model_name", sa.String(length=255), nullable=True),
        sa.Column("default_embedding_model_name", sa.String(length=255), nullable=True),
        sa.Column("discovered_models_json", sa.JSON(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_connections_user_id", "provider_connections", ["user_id"])

    op.add_column("workspaces", sa.Column("default_provider_connection_id", sa.String(length=64), nullable=True))
    op.add_column("workspaces", sa.Column("default_model_name", sa.String(length=255), nullable=True))
    op.add_column("workspaces", sa.Column("default_embedding_model_name", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_workspaces_default_provider_connection",
        "workspaces",
        "provider_connections",
        ["default_provider_connection_id"],
        ["id"],
    )

    op.add_column("conversations", sa.Column("provider_connection_id", sa.String(length=64), nullable=True))
    op.add_column("conversations", sa.Column("model_name", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_conversations_provider_connection",
        "conversations",
        "provider_connections",
        ["provider_connection_id"],
        ["id"],
    )

    op.add_column("skill_definitions", sa.Column("provider_connection_id", sa.String(length=64), nullable=True))
    op.add_column("skill_definitions", sa.Column("model_name", sa.String(length=255), nullable=True))
    op.add_column("skill_definitions", sa.Column("allow_model_override", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_foreign_key(
        "fk_skill_definitions_provider_connection",
        "skill_definitions",
        "provider_connections",
        ["provider_connection_id"],
        ["id"],
    )

    op.add_column("runtime_executions", sa.Column("provider_connection_id", sa.String(length=64), nullable=True))
    op.add_column("runtime_executions", sa.Column("resolved_model_name", sa.String(length=255), nullable=True))
    op.add_column("runtime_executions", sa.Column("resolved_base_url", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_runtime_executions_provider_connection",
        "runtime_executions",
        "provider_connections",
        ["provider_connection_id"],
        ["id"],
    )
    op.create_index("ix_runtime_executions_provider_connection_id", "runtime_executions", ["provider_connection_id"])


def downgrade() -> None:
    op.drop_index("ix_runtime_executions_provider_connection_id", table_name="runtime_executions")
    op.drop_constraint("fk_runtime_executions_provider_connection", "runtime_executions", type_="foreignkey")
    op.drop_column("runtime_executions", "resolved_base_url")
    op.drop_column("runtime_executions", "resolved_model_name")
    op.drop_column("runtime_executions", "provider_connection_id")

    op.drop_constraint("fk_skill_definitions_provider_connection", "skill_definitions", type_="foreignkey")
    op.drop_column("skill_definitions", "allow_model_override")
    op.drop_column("skill_definitions", "model_name")
    op.drop_column("skill_definitions", "provider_connection_id")

    op.drop_constraint("fk_conversations_provider_connection", "conversations", type_="foreignkey")
    op.drop_column("conversations", "model_name")
    op.drop_column("conversations", "provider_connection_id")

    op.drop_constraint("fk_workspaces_default_provider_connection", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "default_embedding_model_name")
    op.drop_column("workspaces", "default_model_name")
    op.drop_column("workspaces", "default_provider_connection_id")

    op.drop_index("ix_provider_connections_user_id", table_name="provider_connections")
    op.drop_table("provider_connections")
