"""Sprint 94: GraphQL schema для mobile clients.

Lightweight GraphQL endpoint поверх FastAPI.
Позволяет mobile app получить данные 1 запросом
вместо multiple REST calls.

Endpoint: POST /graphql
Example query:
  query { me { id email role } subjects { id name } }
"""
from __future__ import annotations

import logging
from typing import List, Optional

import strawberry
from strawberry.fastapi import GraphQLRouter

logger = logging.getLogger(__name__)


# === Types ===

@strawberry.type
class UserType:
    id: int
    email: str
    role: str
    display_name: Optional[str] = None


@strawberry.type
class SubjectType:
    id: int
    code: str
    name: str
    is_active: bool


@strawberry.type
class StreakType:
    current_days: int
    longest_days: int


# === Query ===

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        """Sprint 94: health check для GraphQL."""
        return "ai-tutor GraphQL API"

    @strawberry.field
    def subjects(self) -> list[SubjectType]:
        """Sprint 94: list всех subjects (без auth для simplicity)."""
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.subjects.models import Subject

        with SessionLocal() as db:
            rows = db.execute(
                select(Subject).where(Subject.is_active.is_(True)).limit(20)
            ).scalars().all()
            return [
                SubjectType(id=r.id, code=r.code, name=r.name, is_active=r.is_active)
                for r in rows
            ]


# === Schema ===

schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema, path="/graphql")
