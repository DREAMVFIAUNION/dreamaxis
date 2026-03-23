"""local-open auth, skill packs, knowledge packs, and browser runtime support

Revision ID: 0005_local_open_and_packs
Revises: 0004_cli_runtime_foundation
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_local_open_and_packs"
down_revision = "0004_cli_runtime_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_packs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False, server_default="1.0.0"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="builtin"),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("manifest_path", sa.Text(), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="synced"),
        sa.Column("tool_capabilities_json", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skill_packs_workspace_id", "skill_packs", ["workspace_id"])
    op.create_index("ix_skill_packs_slug", "skill_packs", ["slug"], unique=True)

    op.create_table(
        "knowledge_packs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False, server_default="1.0.0"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="builtin_pack"),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("manifest_path", sa.Text(), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="synced"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_packs_workspace_id", "knowledge_packs", ["workspace_id"])
    op.create_index("ix_knowledge_packs_slug", "knowledge_packs", ["slug"], unique=True)

    op.add_column("agent_roles", sa.Column("default_skill_pack_slugs", sa.JSON(), nullable=True))
    op.add_column("agent_roles", sa.Column("default_knowledge_pack_slugs", sa.JSON(), nullable=True))

    op.add_column("skill_definitions", sa.Column("tool_capabilities", sa.JSON(), nullable=True))
    op.add_column("skill_definitions", sa.Column("knowledge_scope", sa.JSON(), nullable=True))
    op.add_column("skill_definitions", sa.Column("pack_slug", sa.String(length=255), nullable=True))
    op.add_column("skill_definitions", sa.Column("pack_version", sa.String(length=64), nullable=True))
    op.add_column("skill_definitions", sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_skill_definitions_pack_slug", "skill_definitions", ["pack_slug"])

    op.add_column("knowledge_documents", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("knowledge_documents", sa.Column("source_type", sa.String(length=32), nullable=False, server_default="user_upload"))
    op.add_column("knowledge_documents", sa.Column("source_ref", sa.Text(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("knowledge_pack_slug", sa.String(length=255), nullable=True))
    op.create_index("ix_knowledge_documents_knowledge_pack_slug", "knowledge_documents", ["knowledge_pack_slug"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_knowledge_pack_slug", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "knowledge_pack_slug")
    op.drop_column("knowledge_documents", "source_ref")
    op.drop_column("knowledge_documents", "source_type")
    op.drop_column("knowledge_documents", "title")

    op.drop_index("ix_skill_definitions_pack_slug", table_name="skill_definitions")
    op.drop_column("skill_definitions", "is_builtin")
    op.drop_column("skill_definitions", "pack_version")
    op.drop_column("skill_definitions", "pack_slug")
    op.drop_column("skill_definitions", "knowledge_scope")
    op.drop_column("skill_definitions", "tool_capabilities")

    op.drop_column("agent_roles", "default_knowledge_pack_slugs")
    op.drop_column("agent_roles", "default_skill_pack_slugs")

    op.drop_index("ix_knowledge_packs_slug", table_name="knowledge_packs")
    op.drop_index("ix_knowledge_packs_workspace_id", table_name="knowledge_packs")
    op.drop_table("knowledge_packs")

    op.drop_index("ix_skill_packs_slug", table_name="skill_packs")
    op.drop_index("ix_skill_packs_workspace_id", table_name="skill_packs")
    op.drop_table("skill_packs")
