"""Sprint 16.0 P0-2: telegram_bindings в PostgreSQL.

Раньше bot/telegram_bot.py использовал SQLite в /tmp, который терялся
при `docker compose restart` контейнера. Теперь binding chat_id → user_id
хранится в PostgreSQL — persistent.

Backwards compatible: новая таблица, существующие SQLite bindings можно
мигрировать отдельно (Sprint 16.x) или оставить если у вас уже есть
Telegram-юзеры — они перепривяжутся через /start.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_telegram_bindings"
down_revision: Union[str, None] = "0013_secure_exercises"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_bindings",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(20), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_bindings_user_id", "telegram_bindings", ["user_id"])
    op.create_index("ix_telegram_bindings_code", "telegram_bindings", ["code"])


def downgrade() -> None:
    op.drop_index("ix_telegram_bindings_code", table_name="telegram_bindings")
    op.drop_index("ix_telegram_bindings_user_id", table_name="telegram_bindings")
    op.drop_table("telegram_bindings")
