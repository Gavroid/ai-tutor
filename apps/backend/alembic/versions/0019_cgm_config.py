"""Sprint 40: CGM (Continuous Glucose Monitor) integration.

T1D safety design (Luna Pro):
- ❌ НЕ используем AI для medical decisions.
- ❌ НЕ интерпретируем glucose data автоматически.
- ❌ НЕ сохраняем glucose в БД (только проксируем к Nightscout API).
- ✅ ТОЛЬКО display (UI badge), opt-in через cgm_enabled flag.
- ✅ Все glucose readings приходят напрямую из Nightscout.
- ✅ Nightscout API secret НИКОГДА не покидает backend.

Sprint 40 scope:
- CGMConfig (Nightscout URL + enabled flag) per user
- /cgm/latest — proxy к Nightscout /api/v1/entries/sgv
- /cgm/status — proxy к Nightscout /api/v1/status
- Опциональный фронтенд badge (CGMStatus component)
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_cgm_config"
down_revision: Union[str, None] = "0018_source_type_pdf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cgm_configs",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "nightscout_url",
            sa.String(500),
            nullable=False,
            comment="Nightscout API base URL (e.g., https://ns.example.com)",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment="Opt-in: пользователь явно разрешил CGM",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("cgm_configs")