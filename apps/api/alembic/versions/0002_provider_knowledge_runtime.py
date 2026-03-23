"""provider knowledge runtime expansion

Revision ID: 0002_provider_knowledge_runtime
Revises: 0001_mvp_init
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "0002_provider_knowledge_runtime"
down_revision = "0001_mvp_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("llm_models", sa.Column("kind", sa.String(length=32), nullable=False, server_default="chat"))
    op.add_column("llm_models", sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("workspaces", sa.Column("default_provider_id", sa.String(length=64), nullable=True))
    op.add_column("workspaces", sa.Column("default_model_id", sa.String(length=64), nullable=True))
    op.create_foreign_key("fk_workspaces_default_provider", "workspaces", "providers", ["default_provider_id"], ["id"])
    op.create_foreign_key("fk_workspaces_default_model", "workspaces", "llm_models", ["default_model_id"], ["id"])

    op.add_column("conversations", sa.Column("provider_id", sa.String(length=64), nullable=True))
    op.add_column("conversations", sa.Column("model_id", sa.String(length=64), nullable=True))
    op.add_column("conversations", sa.Column("use_knowledge", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key("fk_conversations_provider", "conversations", "providers", ["provider_id"], ["id"])
    op.create_foreign_key("fk_conversations_model", "conversations", "llm_models", ["model_id"], ["id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_documents_workspace_id", "knowledge_documents", ["workspace_id"])

    op.create_table(
        "skill_definitions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provider_id", sa.String(length=64), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("model_id", sa.String(length=64), sa.ForeignKey("llm_models.id"), nullable=True),
        sa.Column("use_knowledge", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skill_definitions_workspace_id", "skill_definitions", ["workspace_id"])

    op.create_table(
        "runtime_executions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column("skill_id", sa.String(length=64), sa.ForeignKey("skill_definitions.id"), nullable=True),
        sa.Column("provider_id", sa.String(length=64), sa.ForeignKey("providers.id"), nullable=True),
        sa.Column("model_id", sa.String(length=64), sa.ForeignKey("llm_models.id"), nullable=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="chat"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("prompt_preview", sa.Text(), nullable=True),
        sa.Column("response_preview", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runtime_executions_workspace_id", "runtime_executions", ["workspace_id"])
    op.create_index("ix_runtime_executions_conversation_id", "runtime_executions", ["conversation_id"])
    op.create_index("ix_runtime_executions_skill_id", "runtime_executions", ["skill_id"])
    op.create_index("ix_runtime_executions_user_id", "runtime_executions", ["user_id"])

    op.add_column("messages", sa.Column("runtime_execution_id", sa.String(length=64), nullable=True))
    op.add_column("messages", sa.Column("sources_json", sa.JSON(), nullable=True))
    op.create_foreign_key("fk_messages_runtime_execution", "messages", "runtime_executions", ["runtime_execution_id"], ["id"])
    op.create_index("ix_messages_runtime_execution_id", "messages", ["runtime_execution_id"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("document_id", sa.String(length=64), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_workspace_id", "knowledge_chunks", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_workspace_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_messages_runtime_execution_id", table_name="messages")
    op.drop_constraint("fk_messages_runtime_execution", "messages", type_="foreignkey")
    op.drop_column("messages", "sources_json")
    op.drop_column("messages", "runtime_execution_id")

    op.drop_index("ix_runtime_executions_user_id", table_name="runtime_executions")
    op.drop_index("ix_runtime_executions_skill_id", table_name="runtime_executions")
    op.drop_index("ix_runtime_executions_conversation_id", table_name="runtime_executions")
    op.drop_index("ix_runtime_executions_workspace_id", table_name="runtime_executions")
    op.drop_table("runtime_executions")

    op.drop_index("ix_skill_definitions_workspace_id", table_name="skill_definitions")
    op.drop_table("skill_definitions")

    op.drop_index("ix_knowledge_documents_workspace_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.drop_constraint("fk_conversations_model", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_provider", "conversations", type_="foreignkey")
    op.drop_column("conversations", "use_knowledge")
    op.drop_column("conversations", "model_id")
    op.drop_column("conversations", "provider_id")

    op.drop_constraint("fk_workspaces_default_model", "workspaces", type_="foreignkey")
    op.drop_constraint("fk_workspaces_default_provider", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "default_model_id")
    op.drop_column("workspaces", "default_provider_id")

    op.drop_column("llm_models", "is_default")
    op.drop_column("llm_models", "kind")
