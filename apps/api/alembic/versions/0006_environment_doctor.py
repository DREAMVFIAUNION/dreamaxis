"""environment doctor, runtime readiness, and skill capability requirements

Revision ID: 0006_environment_doctor
Revises: 0005_local_open_and_packs
Create Date: 2026-03-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_environment_doctor"
down_revision = "0005_local_open_and_packs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runtimes", sa.Column("doctor_status", sa.String(length=32), nullable=True))
    op.add_column("runtimes", sa.Column("last_capability_check_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("skill_definitions", sa.Column("required_capabilities", sa.JSON(), nullable=True))
    op.add_column("skill_definitions", sa.Column("recommended_capabilities", sa.JSON(), nullable=True))
    op.add_column("skill_definitions", sa.Column("workspace_requirements", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("skill_definitions", "workspace_requirements")
    op.drop_column("skill_definitions", "recommended_capabilities")
    op.drop_column("skill_definitions", "required_capabilities")

    op.drop_column("runtimes", "last_capability_check_at")
    op.drop_column("runtimes", "doctor_status")
