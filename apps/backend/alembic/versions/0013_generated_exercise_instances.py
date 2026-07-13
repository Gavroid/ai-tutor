"""Pilot Core Stage 1 — Phase 2 (P1.2.2): generated_exercise_instances.

additive schema change — только новая таблица, никаких правок существующих.
Содержит server-side truth (`correct_answer`, `explanation`) и submission
state. Создаёт индексы для owner/created для быстрого cleanup expired.

Backwards compatible: существующие таблицы не затронуты.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_secure_exercises"
down_revision: Union[str, None] = "0012_rag_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generated_exercise_instances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options_json", sa.Text(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("model", sa.String(100), nullable=False, server_default="mock"),
        sa.Column("prompt_version", sa.String(50), nullable=False, server_default="pilot-1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_answer", sa.Text(), nullable=True),
        sa.Column("submission_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_gei_owner", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"], name="fk_gei_topic", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_generated_exercise_instances_owner_id", "generated_exercise_instances", ["owner_id"])
    op.create_index("ix_generated_exercise_instances_topic_id", "generated_exercise_instances", ["topic_id"])
    op.create_index(
        "ix_gei_owner_created",
        "generated_exercise_instances",
        ["owner_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_gei_owner_created", table_name="generated_exercise_instances")
    op.drop_index("ix_generated_exercise_instances_topic_id", table_name="generated_exercise_instances")
    op.drop_index("ix_generated_exercise_instances_owner_id", table_name="generated_exercise_instances")
    op.drop_table("generated_exercise_instances")
