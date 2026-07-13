"""rag_chunks — Sprint 8.3

Persistence слоя RAG в БД (вместо in-memory).
В MVP был in-memory dict — теряется при рестарте backend.

Структура:
  rag_chunks(id, material_id, hash, text, embedding_json, metadata_json, created_at)
  - hash — sha256(material_id + ':' + text) — уникальный ключ чанка
  - embedding_json — сериализованный список float (для hash-fallback это 384-dim)
  - metadata_json — JSON с subject/topic/grade/etc

Индексы:
  - (material_id) — для быстрого поиска по материалу
  - (hash) UNIQUE — идемпотентность (повторный index того же материала — noop)

Downgrade: drop table — данные теряются, RAG переходит на in-memory (acceptable для dev).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_rag_chunks"
down_revision: Union[str, None] = "0011_badges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("hash", name="uq_rag_chunks_hash"),
    )
    op.create_index("ix_rag_chunks_material", "rag_chunks", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_rag_chunks_material", table_name="rag_chunks")
    op.drop_table("rag_chunks")
