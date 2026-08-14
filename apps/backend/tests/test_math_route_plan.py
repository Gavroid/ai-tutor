import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.math_plan import MATH_SUBJECT_ID
from app.algebra_plan import ALGEBRA_SUBJECT_ID
from app.subjects.scripts_seed_runner import seed_for_tests


def _reset_db():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)


@pytest.fixture()
def seeded_client():
    _reset_db()

    def _gen():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _gen
    session = SessionLocal()
    try:
        seed_for_tests(session, reset=False)
    finally:
        session.close()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_math_route_plan_endpoint_returns_full_route(seeded_client):
    response = seeded_client.get(f"/api/v1/subjects/{MATH_SUBJECT_ID}/route-plan")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 42
    assert data[0]["topic_id"] == 187
    assert data[-1]["topic_id"] == 228
    assert {row["tier"] for row in data} == {"base", "medium", "hard"}
    assert any(row["checkpoint"] for row in data)


def test_algebra_route_plan_endpoint_returns_preview_route(seeded_client):
    response = seeded_client.get(f"/api/v1/subjects/{ALGEBRA_SUBJECT_ID}/route-plan")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 19
    assert data[0]["topic_id"] == 34
    assert data[-1]["topic_id"] == 52
    assert {row["tier"] for row in data} == {"base", "medium", "hard"}
    assert any(row["checkpoint"] for row in data)
    assert data[0]["next_topic_id"] == 35
    assert data[-1]["next_topic_id"] is None


def test_geometry_route_plan_is_empty_until_stage13(seeded_client):
    response = seeded_client.get("/api/v1/subjects/5/route-plan")

    assert response.status_code == 200
    assert response.json() == []
