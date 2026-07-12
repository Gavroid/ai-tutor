"""spaced_repetition — Sprint 2.2

Добавляет поля для интервального повторения (SM-2 алгоритм) в progress:
  - next_review_at    (timestamp) — когда показывать снова
  - last_reviewed_at  (timestamp, nullable) — последний показ
  - review_count      (int) — сколько раз повторяли
  - easiness_factor   (float, default 2.5) — SM-2 EF

Revision ID: 0009_spaced_repetition
Revises: 0008_material_workflow
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_spaced_repetition"
down_revision: Union[str, None] = "0008_material_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("progress") as batch_op:
        batch_op.add_column(
            sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "last_reviewed_at", sa.DateTime(timezone=True), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "review_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "easiness_factor",
                sa.Float(),
                nullable=False,
                server_default=sa.text("2.5"),
            )
        )
        batch_op.create_index(
            "ix_progress_next_review_at", ["next_review_at"]
        )


def downgrade() -> None:
    with op.batch_alter_table("progress") as batch_op:
        batch_op.drop_index("ix_progress_next_review_at")
        batch_op.drop_column("easiness_factor")
        batch_op.drop_column("review_count")
        batch_op.drop_column("last_reviewed_at")
        batch_op.drop_column("next_review_at")
