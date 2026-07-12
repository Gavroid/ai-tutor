"""Тесты Этапа 3: список предметов, темы, подтемы, seed."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects import models
from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS
from app.subjects.scripts_seed_runner import seed_for_tests


def _reset_db():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)


@pytest.fixture()
def seeded_client():
    _reset_db()
    app.dependency_overrides[get_db] = lambda: (lambda: (
        yield SessionLocal()
    ))() or _gen()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    s = SessionLocal()
    try:
        seed_for_tests(s, reset=False)
    finally:
        s.close()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def empty_client():
    _reset_db()

    def _gen():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _gen
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_seed_creates_curriculum(seeded_client):
    s = SessionLocal()
    try:
        subjects = s.scalars(select(models.Subject)).all()
        assert len(subjects) == len(CURRICULUM_7_CLASS) == 12
        assert {x.code for x in subjects} >= {"rus", "algebra", "geom", "phys", "eng", "inf"}
    finally:
        s.close()


def test_list_subjects_returns_seed(seeded_client):
    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 12
    assert data[0]["recommended_grade"] == 7
    codes = {x["code"] for x in data}
    assert codes == {x["code"] for x in CURRICULUM_7_CLASS}


def test_subject_topics_returns_flat_list(seeded_client):
    s = SessionLocal()
    try:
        algebra = s.scalar(select(models.Subject).where(models.Subject.code == "algebra"))
        subj_id = algebra.id
    finally:
        s.close()

    r = seeded_client.get(f"/api/v1/subjects/{subj_id}/topics")
    assert r.status_code == 200
    topics = r.json()
    assert len(topics) > 10
    names = [t["name"] for t in topics]
    assert "Линейное уравнение с одной переменной" in names
    assert "Формулы сокращённого умножения" in names


def test_topic_get(seeded_client):
    s = SessionLocal()
    try:
        t = s.scalar(select(models.Topic).limit(1))
        tid = t.id
    finally:
        s.close()
    r = seeded_client.get(f"/api/v1/topics/{tid}")
    assert r.status_code == 200
    assert r.json()["difficulty"] in (1, 2, 3, 4, 5)


def test_404_for_missing(seeded_client):
    assert seeded_client.get("/api/v1/subjects/99999").status_code == 404
    assert seeded_client.get("/api/v1/topics/99999").status_code == 404


def test_active_only_filter(seeded_client):
    s = SessionLocal()
    try:
        subj = s.scalar(select(models.Subject).limit(1))
        subj.is_active = False
        s.commit()
    finally:
        s.close()

    r = seeded_client.get("/api/v1/subjects?active_only=true")
    assert all(x["is_active"] for x in r.json())
    r = seeded_client.get("/api/v1/subjects?active_only=false")
    inactive = [x for x in r.json() if not x["is_active"]]
    assert len(inactive) >= 1


def test_empty_db_returns_empty_list(empty_client):
    r = empty_client.get("/api/v1/subjects")
    assert r.status_code == 200
    assert r.json() == []