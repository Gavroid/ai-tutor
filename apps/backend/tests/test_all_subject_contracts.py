"""Sprint A: deterministic representative contracts for every subject code."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "all-subject-contract-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("AI_DETERMINISTIC_MODE", "1")
os.environ.setdefault("AI_API_KEY", "mock-key")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
# NOTE: do NOT set AI_BUDGET_REQUESTS_PER_HOUR/DAY/TOKENS at module level —
# that mutates os.environ for every test loaded after us in the same pytest
# process and breaks test_sprint80_hourly_budget (and any other budget test
# that asserts on the default 20 / 200 / 200000 values).
# Per-test budget override is applied via ai_budget.reload_limits(...) inside
# _client().

from fastapi.testclient import TestClient
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.ai import budget as ai_budget
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


class _ClientCM:
    """S0 fix: context-manager wrapper that restores reload_limits() on exit.

    Изначально _client() мутировал ai_budget.HOURLY_REQUESTS_LIMIT = 100_000
    через reload_limits() без teardown — следующие тесты в pytest bundle
    (test_sprint80_hourly_budget) видели 100_000 и падали на assert <= 100.
    """

    def __enter__(self) -> TestClient:
        return _setup_client()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        _teardown_client()


def _setup_client() -> TestClient:
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    session = SessionLocal()
    user_service.register_user(
        session,
        UserCreate(
            email="all-subject-contract@example.com",
            password="strongpass1",
            display_name="Contract Student",
            role="student",  # type: ignore[arg-type]
            grade=7,
        ),
    )
    seed_for_tests(session)
    session.close()

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Поднимаем лимиты для теста, но ОБЯЗАТЕЛЬНО восстанавливаем в teardown,
    # иначе следующие тесты в pytest bundle (например test_sprint80_hourly_budget)
    # увидят 100_000 и упадут.
    ai_budget.reload_limits(
        daily_requests=100_000,
        daily_tokens=10_000_000,
        hourly_requests=100_000,
    )
    ai_budget.reset_budget_state()
    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _teardown_client() -> None:
    """Восстановить дефолтные лимиты и очистить overrides (S0 fix)."""
    ai_budget.reload_limits(
        daily_requests=200,
        daily_tokens=200_000,
        hourly_requests=20,
    )
    ai_budget.reset_budget_state()
    app.dependency_overrides.clear()


def test_all_subjects_explain_and_practice_contract() -> None:
    with _ClientCM() as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "all-subject-contract@example.com", "password": "strongpass1"},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        subjects = client.get("/api/v1/subjects/", headers=headers).json()
        # S1.1 (2026-09-01): curriculum_7_class теперь 16 предметов (добавлены
        # chem/hist-world/lit-2/rus-2 согласно stakeholder D2.1).
        assert len(subjects) == 16

        for subject in subjects:
            topics = client.get(
                f"/api/v1/subjects/{subject['id']}/topics", headers=headers
            ).json()
            assert topics, subject
            topic_id = topics[0]["id"]

            explain = client.post(
                "/api/v1/ai/explain", headers=headers, json={"topic_id": topic_id}
            )
            assert explain.status_code == 200, explain.text
            content = explain.json().get("content", "")
            assert len(content) >= 20
            assert "<think" not in content.lower()
            assert '"correct_answer"' not in content.lower()

            practice = client.post(
                "/api/v2/exercises/generate",
                headers=headers,
                json={"topic_id": topic_id, "difficulty": 2},
            )
            assert practice.status_code == 200, practice.text
            assert "correct_answer" not in practice.json()
