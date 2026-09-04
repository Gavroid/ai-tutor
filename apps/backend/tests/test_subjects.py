"""Тесты Этапа 3: список предметов, темы, подтемы, seed."""
from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only-1234567890")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects import models
from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS
from app.subjects.scripts_seed_runner import seed_for_tests
from fastapi.testclient import TestClient
from sqlalchemy import select


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
        # S1.1 (2026-09-01): curriculum расширен с 12 до 16 (добавлены
        # chem/hist-world/lit-2/rus-2 согласно stakeholder D2.1).
        assert len(subjects) == len(CURRICULUM_7_CLASS) == 16
        assert {x.code for x in subjects} >= {"rus", "algebra", "geom", "phys", "eng", "inf", "chem", "hist-world", "lit-2", "rus-2"}
    finally:
        s.close()


def test_list_subjects_returns_seed(seeded_client):
    """Sprint 3.9.3 (2026-08-22): все 16 subjects promoted после reviewed_auto mapping + smoke.

    SubjectOut возвращает явные evidence-поля и mvp_status. Ребёнку видны
    все 16 subjects (math, algebra, geom, phys, inf, rus, rus-2, hist, hist-world,
    eng, lit, lit-2, bio, soc, geo, chem).
    """
    from app.subjects import evidence as _ev_seed
    _ev_seed.reset_evidence_cache()
    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200
    data = r.json()
    # S1.1 (2026-09-01): curriculum теперь 16 (добавлены chem/hist-world/
    # lit-2/rus-2 согласно stakeholder D2.1).
    assert len(data) == 16
    assert data[0]["recommended_grade"] == 7
    codes = {x["code"] for x in data}
    assert codes == {x["code"] for x in CURRICULUM_7_CLASS}
    for subj in data:
        # Sprint 3.9.3: все 16 subjects промоучены (PILOT_SCOPE расширен).
        assert subj["mvp_status"] == "mvp_ready"
        assert subj["pilot_visible"] is True
        assert subj["promotion_allowed"] is True
        assert subj["manifest_ready"] is True
        assert subj["mapping_ready"] is True
        assert subj["import_ready"] is True
        assert subj["rag_ready"] is True
        assert subj["practice_ready"] is True
        # manual_smoke_ready честный: в persisted evidence — true для всех 16.
        assert subj["manual_smoke_ready"] is True


def test_pilot_visible_only_for_math_after_evidence_policy(seeded_client):
    """Sprint 3.9.3 (2026-08-22): все 16 subjects promoted.

    Этот тест проверяет, что promotion_allowed инвариантно требует все gates закрытыми
    (не обходит через counts), и что в текущей persisted evidence все 16 codes
    прошли promotion.
    """
    from app.subjects import evidence as _ev_pol
    _ev_pol.reset_evidence_cache()
    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200
    data = r.json()
    # Sprint 3.9.3: все 16 subjects promoted (persisted evidence).
    pilot_codes = sorted([x["code"] for x in data if x["pilot_visible"]])
    expected = sorted([s["code"] for s in CURRICULUM_7_CLASS])
    assert pilot_codes == expected
    promotion_codes = sorted([x["code"] for x in data if x["promotion_allowed"]])
    assert promotion_codes == pilot_codes


def test_evidence_load_from_json_overrides_default_policy(seeded_client, tmp_path, monkeypatch):
    """Если evidence.json существует, его значения используются вместо default policy."""
    import json as json_mod

    from app.subjects import evidence as evidence_mod
    evidence_mod.reset_evidence_cache()

    payload = {
        "math": {
            "manifest_ready": True,
            "mapping_ready": True,
            "import_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "manual_smoke_ready": True,
            "pilot_visible": False,
            "promotion_allowed": False,
            "blocked_reason": None,
        },
        "algebra": {
            "manifest_ready": False,
            "mapping_ready": False,
            "import_ready": False,
            "rag_ready": False,
            "practice_ready": False,
            "manual_smoke_ready": False,
            "pilot_visible": False,
            "promotion_allowed": False,
            "blocked_reason": None,
        },
    }
    # Подменяем loader.
    monkeypatch.setattr(
        "app.subjects.evidence._try_load_evidence_json",
        lambda: {code: evidence_mod.SubjectEvidence(
            code=code,
            manifest_ready=bool(row.get("manifest_ready", False)),
            mapping_ready=bool(row.get("mapping_ready", False)),
            import_ready=bool(row.get("import_ready", False)),
            rag_ready=bool(row.get("rag_ready", False)),
            practice_ready=bool(row.get("practice_ready", False)),
            manual_smoke_ready=bool(row.get("manual_smoke_ready", False)),
            pilot_visible=bool(row.get("pilot_visible", False)),
            promotion_allowed=bool(row.get("promotion_allowed", False)),
            blocked_reason=row.get("blocked_reason"),
        ) for code, row in payload.items()},
    )
    evidence_mod.reset_evidence_cache()

    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200
    data = r.json()
    math = next(x for x in data if x["code"] == "math")
    algebra = next(x for x in data if x["code"] == "algebra")
    # Math отозван: mvp_status != mvp_ready, pilot_visible=false.
    assert math["mvp_status"] != "mvp_ready"
    assert math["pilot_visible"] is False
    # Algebra всё ещё preview (все gates false).
    assert algebra["mvp_status"] == "preview"
    assert algebra["pilot_visible"] is False
    assert algebra["manifest_ready"] is False


def test_evidence_load_from_json_overrides_default_policy(seeded_client, tmp_path, monkeypatch):
    """Если evidence.json существует, его значения используются вместо default policy."""
    import json as json_mod

    from app.subjects import evidence as evidence_mod

    payload = {
        "math": {
            "manifest_ready": True,
            "mapping_ready": True,
            "import_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "manual_smoke_ready": True,
            "pilot_visible": False,  # отзыв pilot-visible
            "promotion_allowed": False,
            "blocked_reason": None,
        },
        "algebra": {
            "manifest_ready": True,
            "mapping_ready": True,
            "import_ready": True,
            "rag_ready": True,
            "practice_ready": True,
            "manual_smoke_ready": True,
            "pilot_visible": True,
            "promotion_allowed": True,
            "blocked_reason": None,
        },
    }
    evidence_file = tmp_path / "evidence.json"
    evidence_file.write_text(json_mod.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(evidence_mod, "_evidence_cache", None)
    # Подменяем путь поиска на tmp_path.
    monkeypatch.setattr(
        "app.subjects.evidence._try_load_evidence_json",
        lambda: {code: evidence_mod.SubjectEvidence(
            code=code,
            manifest_ready=bool(row.get("manifest_ready", False)),
            mapping_ready=bool(row.get("mapping_ready", False)),
            import_ready=bool(row.get("import_ready", False)),
            rag_ready=bool(row.get("rag_ready", False)),
            practice_ready=bool(row.get("practice_ready", False)),
            manual_smoke_ready=bool(row.get("manual_smoke_ready", False)),
            pilot_visible=bool(row.get("pilot_visible", False)),
            promotion_allowed=bool(row.get("promotion_allowed", False)),
            blocked_reason=row.get("blocked_reason"),
        ) for code, row in payload.items()},
    )
    evidence_mod.reset_evidence_cache()

    r = seeded_client.get("/api/v1/subjects")
    assert r.status_code == 200
    data = r.json()
    math = next(x for x in data if x["code"] == "math")
    algebra = next(x for x in data if x["code"] == "algebra")
    # Math отозван: mvp_ready=False, pilot_visible=False.
    assert math["mvp_status"] != "mvp_ready"
    assert math["pilot_visible"] is False
    # Algebra промоучена в этом тесте.
    assert algebra["mvp_status"] == "mvp_ready"
    assert algebra["pilot_visible"] is True
    assert algebra["promotion_allowed"] is True


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


def test_algebra_does_not_become_mvp_ready_without_explicit_evidence(seeded_client, tmp_path, monkeypatch):
    """Sprint 3.9.3 (2026-08-22): инвариант fail-closed.

    Даже при полном coverage route/source/practice algebra НЕ должна автоматически
    становиться mvp_ready без явного evidence в evidence.json. Этот тест изолирует
    persisted evidence через tmp_path и проверяет, что canonical derivation НЕ
    даёт promotion когда evidence не задан.
    """
    from app.rag_models import RagChunk
    from app.subjects import evidence as evidence_mod
    from app.teacher import content_registry

    # Изоляция: подменяем loader на пустой (нет evidence для algebra).
    monkeypatch.setattr(
        "app.subjects.evidence._try_load_evidence_json",
        lambda: {},  # ничего не вернётся
    )
    evidence_mod.reset_evidence_cache()

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

    # Diagnostic counts — есть.
    assert algebra["route_ready"] is True
    assert algebra["source_topic_count"] == 19
    assert algebra["practice_topic_count"] == 19
    # Без evidence в evidence.json algebra не promoted.
    assert algebra["promotion_allowed"] is False
    assert algebra["pilot_visible"] is False
    assert algebra["mvp_status"] != "mvp_ready"


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
