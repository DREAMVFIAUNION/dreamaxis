"""cli runtime foundation and agent role registry

Revision ID: 0004_cli_runtime_foundation
Revises: 0003_provider_connections
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_cli_runtime_foundation"
down_revision = "0003_provider_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("workspace_root_path", sa.Text(), nullable=True))

    op.create_table(
        "agent_roles",
        sa.Column("slug", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("allowed_skill_modes", sa.JSON(), nullable=True),
        sa.Column("allowed_runtime_types", sa.JSON(), nullable=True),
        sa.Column("default_model_binding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "runtimes",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("runtime_type", sa.String(length=32), nullable=False, server_default="cli"),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False, server_default="workspace"),
        sa.Column("scope_ref_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="online"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runtimes_scope_ref_id", "runtimes", ["scope_ref_id"])

    op.create_table(
        "runtime_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_type", sa.String(length=32), nullable=False, server_default="cli"),
        sa.Column("runtime_id", sa.String(length=64), sa.ForeignKey("runtimes.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("reusable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runtime_sessions_runtime_id", "runtime_sessions", ["runtime_id"])
    op.create_index("ix_runtime_sessions_workspace_id", "runtime_sessions", ["workspace_id"])
    op.create_index("ix_runtime_sessions_created_by_id", "runtime_sessions", ["created_by_id"])

    op.create_table(
        "runtime_session_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("runtime_session_id", sa.String(length=64), sa.ForeignKey("runtime_sessions.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runtime_session_events_runtime_session_id", "runtime_session_events", ["runtime_session_id"])

    op.add_column("skill_definitions", sa.Column("skill_mode", sa.String(length=32), nullable=False, server_default="prompt"))
    op.add_column("skill_definitions", sa.Column("required_runtime_type", sa.String(length=32), nullable=True))
    op.add_column("skill_definitions", sa.Column("session_mode", sa.String(length=32), nullable=False, server_default="reuse"))
    op.add_column("skill_definitions", sa.Column("command_template", sa.Text(), nullable=True))
    op.add_column("skill_definitions", sa.Column("working_directory", sa.String(length=512), nullable=True))
    op.add_column("skill_definitions", sa.Column("agent_role_slug", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_skill_definitions_agent_roles",
        "skill_definitions",
        "agent_roles",
        ["agent_role_slug"],
        ["slug"],
    )

    op.add_column("runtime_executions", sa.Column("runtime_id", sa.String(length=64), nullable=True))
    op.add_column("runtime_executions", sa.Column("runtime_session_id", sa.String(length=64), nullable=True))
    op.add_column("runtime_executions", sa.Column("execution_kind", sa.String(length=32), nullable=False, server_default="chat"))
    op.add_column("runtime_executions", sa.Column("command_preview", sa.Text(), nullable=True))
    op.add_column("runtime_executions", sa.Column("artifacts_json", sa.JSON(), nullable=True))
    op.create_foreign_key(
        "fk_runtime_executions_runtimes",
        "runtime_executions",
        "runtimes",
        ["runtime_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_runtime_executions_runtime_sessions",
        "runtime_executions",
        "runtime_sessions",
        ["runtime_session_id"],
        ["id"],
    )
    op.create_index("ix_runtime_executions_runtime_id", "runtime_executions", ["runtime_id"])
    op.create_index("ix_runtime_executions_runtime_session_id", "runtime_executions", ["runtime_session_id"])


def downgrade() -> None:
    op.drop_index("ix_runtime_executions_runtime_session_id", table_name="runtime_executions")
    op.drop_index("ix_runtime_executions_runtime_id", table_name="runtime_executions")
    op.drop_constraint("fk_runtime_executions_runtime_sessions", "runtime_executions", type_="foreignkey")
    op.drop_constraint("fk_runtime_executions_runtimes", "runtime_executions", type_="foreignkey")
    op.drop_column("runtime_executions", "artifacts_json")
    op.drop_column("runtime_executions", "command_preview")
    op.drop_column("runtime_executions", "execution_kind")
    op.drop_column("runtime_executions", "runtime_session_id")
    op.drop_column("runtime_executions", "runtime_id")

    op.drop_constraint("fk_skill_definitions_agent_roles", "skill_definitions", type_="foreignkey")
    op.drop_column("skill_definitions", "agent_role_slug")
    op.drop_column("skill_definitions", "working_directory")
    op.drop_column("skill_definitions", "command_template")
    op.drop_column("skill_definitions", "session_mode")
    op.drop_column("skill_definitions", "required_runtime_type")
    op.drop_column("skill_definitions", "skill_mode")

    op.drop_index("ix_runtime_session_events_runtime_session_id", table_name="runtime_session_events")
    op.drop_table("runtime_session_events")

    op.drop_index("ix_runtime_sessions_created_by_id", table_name="runtime_sessions")
    op.drop_index("ix_runtime_sessions_workspace_id", table_name="runtime_sessions")
    op.drop_index("ix_runtime_sessions_runtime_id", table_name="runtime_sessions")
    op.drop_table("runtime_sessions")

    op.drop_index("ix_runtimes_scope_ref_id", table_name="runtimes")
    op.drop_table("runtimes")

    op.drop_table("agent_roles")
    op.drop_column("workspaces", "workspace_root_path")
