"""material_workflow — Sprint 1.4

Добавляет workflow-поля в learning_materials:
  - status           (draft / ai_generated / teacher_approved / published)
  - generated_by     (FK users.id, nullable)
  - approved_by      (FK users.id, nullable)
  - published_at     (timestamp, nullable)
  - source_type      (text / file / topic)
  - ai_confidence    (TEXT / JSON) — что AI пометил как "не уверен"

Все nullable + default'ы — чтобы существующие записи не сломались.

Используем batch_alter_table для совместимости с SQLite (тесты in-memory),
где ALTER TABLE с FK-constraint не поддерживается напрямую.

Revision ID: 0008_material_workflow
Revises: 0007_password_reset
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_material_workflow"
down_revision: Union[str, None] = "0007_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite не поддерживает ADD CONSTRAINT в ALTER — используем batch mode,
    # который работает через copy-and-rename для всех диалектов одинаково.
    with op.batch_alter_table("learning_materials") as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'draft'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "generated_by",
                sa.BigInteger(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "approved_by",
                sa.BigInteger(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "source_type",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'text'"),
            )
        )
        batch_op.add_column(sa.Column("ai_confidence", sa.Text(), nullable=True))
        batch_op.create_index(
            "ix_learning_materials_status", ["status"]
        )
        batch_op.create_index(
            "ix_learning_materials_topic_status", ["topic_id", "status"]
        )
        batch_op.create_index(
            "ix_learning_materials_generated_by", ["generated_by"]
        )
        # FK constraints — отдельными вызовами с именами (batch mode требует имя).
        batch_op.create_foreign_key(
            "fk_learning_materials_generated_by",
            "users",
            ["generated_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_learning_materials_approved_by",
            "users",
            ["approved_by"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("learning_materials") as batch_op:
        batch_op.drop_constraint(
            "fk_learning_materials_approved_by", type_="foreignkey"
        )
        batch_op.drop_constraint(
            "fk_learning_materials_generated_by", type_="foreignkey"
        )
        batch_op.drop_index("ix_learning_materials_generated_by")
        batch_op.drop_index("ix_learning_materials_topic_status")
        batch_op.drop_index("ix_learning_materials_status")
        batch_op.drop_column("ai_confidence")
        batch_op.drop_column("source_type")
        batch_op.drop_column("published_at")
        batch_op.drop_column("approved_by")
        batch_op.drop_column("generated_by")
        batch_op.drop_column("status")
