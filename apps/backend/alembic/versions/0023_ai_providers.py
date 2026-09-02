"""Sprint 3.9.6 — AI-connections: мульти-провайдер + per-subject модель + fallback.

Добавляет таблицы:
- ai_providers: подключения к AI-сервисам (OpenRouter, Groq, OpenAI...)
- ai_model_catalog: модели выбранные у провайдера (по выбору админа)
- subject_ai_models: назначение модели на предмет (primary / fallback)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_ai_providers"
down_revision: Union[str, None] = "0022_feedback_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_providers
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("kind", sa.String(32), nullable=False, server_default="openai_compat"),
        sa.Column("base_url", sa.String(255), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ai_model_catalog
    op.create_table(
        "ai_model_catalog",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "provider_id",
            sa.BigInteger,
            sa.ForeignKey("ai_providers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider_id", "model_name", name="uq_model_provider_name"),
    )

    # subject_ai_models
    op.create_table(
        "subject_ai_models",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "subject_id",
            sa.BigInteger,
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model_id",
            sa.BigInteger,
            sa.ForeignKey("ai_model_catalog.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False, server_default="primary"),
        sa.UniqueConstraint("subject_id", "role", name="uq_subject_role"),
    )


def downgrade() -> None:
    op.drop_table("subject_ai_models")
    op.drop_table("ai_model_catalog")
    op.drop_table("ai_providers")
