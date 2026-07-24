"""Sprint 19 P2-2: checker_type для generated_exercise_instances.

Добавляет колонку `checker_type` (numeric/keyword/exact/semantic) и
`reference_solution` в generated_exercise_instances, чтобы диспатчер
мог выбрать правильную стратегию проверки ответа.

Backwards compatible: новые колонки nullable, default = 'keyword'.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_exercise_checker_type"
down_revision: Union[str, None] = "0014_telegram_bindings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_exercise_instances",
        sa.Column("checker_type", sa.String(20), nullable=False, server_default="keyword"),
    )
    op.add_column(
        "generated_exercise_instances",
        sa.Column("reference_solution", sa.Text(), nullable=True),
    )
    op.add_column(
        "generated_exercise_instances",
        sa.Column("required_keywords", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generated_exercise_instances", "required_keywords")
    op.drop_column("generated_exercise_instances", "reference_solution")
    op.drop_column("generated_exercise_instances", "checker_type")
