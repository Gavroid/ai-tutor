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
    math = next(x for x in data if x["code"] == "math")
    algebra = next(x for x in data if x["code"] == "algebra")
    assert math["mvp_status"] == "mvp_ready"
    assert math["rag_ready"] is True
    assert math["practice_ready"] is True
    assert math["route_ready"] is True
    assert math["topic_count"] == 42
    assert math["source_topic_count"] == 42
    assert math["practice_topic_count"] == 42
    assert algebra["mvp_status"] == "preview"
    assert algebra["route_ready"] is True
    assert algebra["rag_ready"] is False
    assert algebra["practice_ready"] is False
    assert algebra["topic_count"] == 19
    assert algebra["source_topic_count"] == 0
    assert algebra["practice_topic_count"] == 0
    geometry = next(x for x in data if x["code"] == "geom")
    assert geometry["mvp_status"] == "preview"
    assert geometry["route_ready"] is True
    assert geometry["rag_ready"] is False
    assert geometry["practice_ready"] is False
    assert geometry["topic_count"] == 13
    assert geometry["source_topic_count"] == 0
    assert geometry["practice_topic_count"] == 0


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


def test_topic_followups_returns_backend_managed_buttons(seeded_client):
    s = SessionLocal()
    try:
        topic = s.scalar(select(models.Topic).where(models.Topic.name == "Среднее арифметическое"))
        assert topic is not None
        topic_id = topic.id
    finally:
        s.close()

    r = seeded_client.get(f"/api/v1/topics/{topic_id}/followups")

    assert r.status_code == 200
    data = r.json()
    assert [x["label"] for x in data] == ["Среднее чисел", "Средняя скорость", "Средний вес"]
    assert all(x["prompt"] for x in data)


def test_topic_followups_unknown_topic_returns_empty(seeded_client):
    s = SessionLocal()
    try:
        t = s.scalar(select(models.Topic).where(models.Topic.name == "Формулы сокращённого умножения"))
        assert t is not None
        tid = t.id
    finally:
        s.close()

    r = seeded_client.get(f"/api/v1/topics/{tid}/followups")

    assert r.status_code == 200
    assert r.json() == []


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


def test_algebra_becomes_mvp_ready_when_route_source_and_practice_coverage_complete(seeded_client, monkeypatch):
    from app.rag_models import RagChunk
    from app.teacher import content_registry

    s = SessionLocal()
    try:
        algebra = s.scalar(select(models.Subject).where(models.Subject.code == "algebra"))
        assert algebra is not None
        topic_ids = [topic.id for section in algebra.sections for topic in section.topics]
        assert len(topic_ids) == 19
        for idx, topic_id in enumerate(topic_ids, start=1):
            material = models.LearningMaterial(
                id=50000 + idx,
                topic_id=topic_id,
                title=f"Algebra source {topic_id}",
                content="Verified algebra source text",
                source="algebra-test",
                status="published",
                source_type="text",
            )
            s.add(material)
            s.flush()
            s.add(
                RagChunk(
                    material_id=material.id,
                    hash=f"algebra-test-{topic_id}",
                    text="Verified algebra source text",
                    embedding_json="[]",
                    metadata_json=f'{{"subject_code":"algebra","topic_id":{topic_id},"topic_name":"topic","source_title":"Algebra source","source_section":"unit","license":"CC BY 4.0","attribution":"test"}}',
                )
            )
        s.commit()
    finally:
        s.close()

    monkeypatch.setattr(content_registry, "get_fallbacks", lambda topic_id: [object()])

    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200
    algebra = next(x for x in r.json() if x["code"] == "algebra")

    assert algebra["route_ready"] is True
    assert algebra["rag_ready"] is True
    assert algebra["practice_ready"] is True
    assert algebra["source_topic_count"] == 19
    assert algebra["practice_topic_count"] == 19
    assert algebra["mvp_status"] == "mvp_ready"


def test_all_seeded_subjects_have_route_coverage(seeded_client):
    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200

    for subject in r.json():
        assert subject["topic_count"] > 0
        assert subject["route_ready"] is True
        assert subject["route_topic_count"] == subject["topic_count"]


def test_generic_subject_route_plan_returns_curriculum_topics(seeded_client):
    s = SessionLocal()
    try:
        rus = s.scalar(select(models.Subject).where(models.Subject.code == "rus"))
        assert rus is not None
        subject_id = rus.id
        topic_count = sum(len(section.topics) for section in rus.sections)
    finally:
        s.close()

    r = seeded_client.get(f"/api/v1/subjects/{subject_id}/route-plan")

    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == topic_count == 13
    assert rows[0]["topic_id"]
    assert rows[0]["order"] == 1
    assert rows[0]["section"]
    assert rows[0]["focus"]
    assert rows[0]["next_topic_id"] == rows[1]["topic_id"]
