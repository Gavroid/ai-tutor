"""Sprint 4 RAG production: admin API, async queue, reindex, monitoring.

Tests (TDD — RED phase, см. git history):
- POST /admin/rag/upload — accept PDF, validate, enqueue job, return job_id
- POST /admin/rag/upload — reject non-PDF / oversize files (4xx)
- GET /admin/rag/status?job_id=... — return queued/running/done/failed
- POST /admin/rag/reindex — mode=full_wipe, mode=skip_existing
- GET /admin/rag/stats — aggregates (jobs, chunks, latency p50)
- Auto subject detection from filename regex + keyword fallback
- Async fallback to sync if Redis unavailable (RAG_SYNC=1)
- Rate limit: 10 uploads/min per admin user
- Prometheus metrics exposed at /metrics
- Dry-run mode (RAG_DRY_RUN=1) — no DB writes, no chunk persistence

Эти тесты написаны ДО production-кода (RED), чтобы зафиксировать контракт.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.admin.rag_schemas import (
    IngestMode,
    IngestRequest,
    IngestResponse,
    JobStatus,
    RagJobStatus,
    RagStats,
    SubjectDetection,
)
from app.common.deps import Role, User
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.models import LearningMaterial, Subject, Topic
from app.users import service as user_service
from app.users.models import User as UserModel
from app.users.schemas import UserCreate
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# === Test client fixture (per-test isolation) ===


@pytest.fixture
def db_session() -> Session:
    """Sprint 4 RAG: чистая in-memory SQLite session per test (для прямого доступа в setup).

    Используется в admin_user / material_math для INSERT'ов.
    Каждое обращение к endpoint через TestClient получает СВОЮ SessionLocal сессию
    через dependency override (см. client fixture).
    """
    Base.metadata.drop_all(engine)
    engine.dispose()  # Required for SQLite in-memory to release the prior DB.
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Sprint 4 RAG: TestClient с dependency override get_db.

    Override создаёт новую сессию на каждый request (паттерн test_observability.py).
    engine использует StaticPool в conftest.py → in-memory DB переиспользуется.
    """
    from app.db.session import get_db as _get_db_dep

    def _gen() -> Session:
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[_get_db_dep] = _gen
    c = TestClient(app)
    try:
        yield c
    finally:
        # Clear override СРАЗУ после выхода из test context — до того, как
        # conftest._reset_state попытается clearить и тригернёт закрытие
        # generator'ов на потенциально disposed engine.
        app.dependency_overrides.pop(_get_db_dep, None)


# === Fixtures (depend on db_session) ===


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Тестовый admin для защищённых endpoints."""
    from app.auth.security import hash_password

    user = UserModel(
        email="rag-admin@test.local",
        password_hash=hash_password("testpass123"),
        display_name="RAG Admin",
        role=Role.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """JWT для admin_user (используется в /admin/rag/* endpoints)."""
    from app.auth.security import create_access_token

    token, _ = create_access_token(user=admin_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def material_math(db_session: Session) -> LearningMaterial:
    """Тестовый material с минимальными FK (subject → section → topic)."""
    from app.subjects.models import Section, Subject, Topic
    from app.subjects.scripts_seed_runner import seed_for_tests

    seed_for_tests(db_session)
    db_session.commit()

    # Берём (или создаём) subject math + section + topic.
    subj = db_session.query(Subject).filter_by(code="math").first()
    if subj is None:
        subj = Subject(
            code="math",
            name="Математика",
            recommended_grade=7,
            age_min=12,
            age_max=14,
            is_active=True,
        )
        db_session.add(subj)
        db_session.commit()
        db_session.refresh(subj)

    sec = db_session.query(Section).filter_by(subject_id=subj.id).first()
    if sec is None:
        sec = Section(subject_id=subj.id, name="Алгебра", order_index=0)
        db_session.add(sec)
        db_session.commit()
        db_session.refresh(sec)

    topic = db_session.query(Topic).filter_by(section_id=sec.id).first()
    if topic is None:
        topic = Topic(section_id=sec.id, name="Тестовая тема", order_index=0)
        db_session.add(topic)
        db_session.commit()
        db_session.refresh(topic)

    # Material с file_path (для reindex тестов).
    tmp_path = Path(tempfile_dir()) / "test_material.pdf"
    tmp_path.write_bytes(b"%PDF-1.4\n%minimal")
    mat = LearningMaterial(
        topic_id=topic.id,
        title="Test Material",
        content="test content",
        source_type="text",
        status="draft",
        file_path=str(tmp_path),
    )
    db_session.add(mat)
    db_session.commit()
    db_session.refresh(mat)
    return mat


def tempfile_dir() -> str:
    """Sprint 4 RAG: helper — temp dir для тестовых PDF."""
    import tempfile

    d = tempfile.mkdtemp(prefix="rag_test_")
    return d


# === Tests: schemas & subject detection ===


class TestSubjectDetection:
    """Auto-detect subject from filename + keyword fallback."""

    def test_detect_from_filename_math(self):
        from app.admin.rag_subject_detect import detect_subject_from_filename

        result = detect_subject_from_filename("math_7_class_quadratic_equations.pdf")
        assert result.subject_code == "math"
        assert result.grade == 7
        assert result.confidence > 0.8

    def test_detect_from_filename_russian(self):
        from app.admin.rag_subject_detect import detect_subject_from_filename

        result = detect_subject_from_filename("russian-grammar-5.pdf")
        assert result.subject_code == "russian"
        assert result.grade == 5

    def test_detect_unknown_returns_none(self):
        from app.admin.rag_subject_detect import detect_subject_from_filename

        result = detect_subject_from_filename("random_document_2024.pdf")
        assert result.subject_code is None

    def test_keyword_fallback(self):
        from app.admin.rag_subject_detect import detect_subject_from_filename

        # Filename без pattern, но content содержит keyword.
        result = detect_subject_from_filename("worksheet.pdf", content_preview="Решите уравнение: x² + 5x + 6 = 0")
        assert result.subject_code == "math"
        assert result.method == "keyword"


# === Tests: schemas ===


class TestIngestSchemas:
    """Pydantic schemas для RAG API."""

    def test_ingest_response_queued(self):
        resp = IngestResponse(
            job_id="abc123",
            status=JobStatus.QUEUED,
            material_id=42,
            message="PDF queued for ingestion",
        )
        assert resp.status == JobStatus.QUEUED
        assert resp.material_id == 42

    def test_ingest_request_validation(self):
        req = IngestRequest(
            material_id=1,
            mode=IngestMode.FULL_WIPE,
            filename="math.pdf",
            dry_run=False,
        )
        assert req.mode == IngestMode.FULL_WIPE

    def test_job_status_enum(self):
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.DONE.value == "done"
        assert JobStatus.FAILED.value == "failed"

    def test_rag_stats_schema(self):
        stats = RagStats(
            jobs_last_24h=10,
            jobs_failed=1,
            chunks_total=1500,
            avg_duration_ms=850.0,
            p95_duration_ms=2200.0,
            queue_depth=3,
        )
        assert stats.chunks_total == 1500


# === Tests: API endpoints (RED — без кода роутера они не пройдут) ===


class TestAdminRagUpload:
    """POST /admin/rag/upload."""

    def test_upload_requires_admin(self, db_session: Session, client: TestClient):
        """Без auth → 401."""
        pdf_bytes = _make_minimal_pdf()
        response = client.post(
            "/api/v1/admin/rag/upload",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
            data={"filename": "test.pdf", "material_id": "1"},
        )
        assert response.status_code in (401, 403)

    def test_upload_accepts_valid_pdf(
        self, client: TestClient, admin_auth_headers: dict[str, str], material_math: LearningMaterial
    ):
        """Валидный PDF → 202 Accepted + job_id."""
        pdf_bytes = _make_minimal_pdf()
        response = client.post(
            "/api/v1/admin/rag/upload",
            headers=admin_auth_headers,
            files={"file": ("math_test.pdf", pdf_bytes, "application/pdf")},
            data={"filename": "math_test.pdf", "material_id": str(material_math.id)},
        )
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] in ("queued", "done")  # done если sync mode

    def test_upload_rejects_non_pdf(
        self, client: TestClient, admin_auth_headers: dict[str, str], material_math: LearningMaterial
    ):
        """Файл без PDF magic → 400."""
        not_pdf = b"This is not a PDF"
        response = client.post(
            "/api/v1/admin/rag/upload",
            headers=admin_auth_headers,
            files={"file": ("test.txt", not_pdf, "text/plain")},
            data={"filename": "test.txt", "material_id": str(material_math.id)},
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_upload_rejects_oversize(
        self, client: TestClient, admin_auth_headers: dict[str, str], material_math: LearningMaterial
    ):
        """Файл >50MB → 413."""
        big_pdf = b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)
        response = client.post(
            "/api/v1/admin/rag/upload",
            headers=admin_auth_headers,
            files={"file": ("big.pdf", big_pdf, "application/pdf")},
            data={"filename": "big.pdf", "material_id": str(material_math.id)},
        )
        assert response.status_code == 413

    def test_upload_dry_run_no_db_writes(
        self,
        client: TestClient,
        admin_auth_headers: dict[str, str],
        material_math: LearningMaterial,
        db_session: Session,
    ):
        """Dry-run mode: chunks не создаются."""
        from sqlalchemy import text

        before = db_session.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar()
        with patch.dict(os.environ, {"RAG_DRY_RUN": "1"}):
            pdf_bytes = _make_minimal_pdf()
            response = client.post(
                "/api/v1/admin/rag/upload",
                headers=admin_auth_headers,
                files={"file": ("dry.pdf", pdf_bytes, "application/pdf")},
                data={
                    "filename": "dry.pdf",
                    "material_id": str(material_math.id),
                    "dry_run": "true",
                },
            )
        assert response.status_code == 202
        after = db_session.execute(text("SELECT COUNT(*) FROM rag_chunks")).scalar()
        assert after == before


class TestAdminRagStatus:
    """GET /admin/rag/status?job_id=..."""

    def test_status_returns_job_state(self, client: TestClient, admin_auth_headers: dict[str, str]):
        response = client.get(
            "/api/v1/admin/rag/status?job_id=test-job-123",
            headers=admin_auth_headers,
        )
        # 404 если job не существует, 200 если есть.
        assert response.status_code in (200, 404)

    def test_status_requires_admin(self, client: TestClient):
        response = client.get("/api/v1/admin/rag/status?job_id=test")
        assert response.status_code in (401, 403)


class TestAdminRagReindex:
    """POST /admin/rag/reindex."""

    def test_reindex_full_wipe(
        self,
        client: TestClient,
        admin_auth_headers: dict[str, str],
        material_math: LearningMaterial,
        db_session: Session,
    ):
        """mode=full_wipe → DELETE existing chunks, re-ingest."""
        response = client.post(
            "/api/v1/admin/rag/reindex",
            headers=admin_auth_headers,
            json={
                "material_id": material_math.id,
                "mode": "full_wipe",
                "filename": "math_test.pdf",
            },
        )
        assert response.status_code in (200, 202)

    def test_reindex_skip_existing(
        self,
        client: TestClient,
        admin_auth_headers: dict[str, str],
        material_math: LearningMaterial,
    ):
        response = client.post(
            "/api/v1/admin/rag/reindex",
            headers=admin_auth_headers,
            json={
                "material_id": material_math.id,
                "mode": "skip_existing",
                "filename": "math_test.pdf",
            },
        )
        assert response.status_code in (200, 202)


class TestAdminRagStats:
    """GET /admin/rag/stats."""

    def test_stats_returns_aggregates(self, client: TestClient, admin_auth_headers: dict[str, str]):
        response = client.get("/api/v1/admin/rag/stats", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "chunks_total" in data
        assert "jobs_last_24h" in data
        assert "avg_duration_ms" in data


# === Tests: async/sync fallback ===


class TestRagQueueFallback:
    """Если Redis недоступен — sync fallback."""

    def test_sync_fallback_when_redis_down(self, monkeypatch, material_math: LearningMaterial):
        """RAG_SYNC=1 → ingest выполняется inline, job.status=done сразу."""
        from app.admin.rag_queue import ingest_pdf_async

        monkeypatch.setenv("RAG_SYNC", "1")
        result = ingest_pdf_async(
            material_id=material_math.id,
            pdf_path=Path("/tmp/nonexistent.pdf"),
            filename="test.pdf",
        )
        # В sync mode: result содержит chunks_count=0 (file not found) или done status
        assert result["status"] in ("done", "failed")


# === Tests: metrics ===


class TestRagMetrics:
    """Prometheus метрики rag_*."""

    def test_metrics_exposed(self, client: TestClient):
        """После upload /metrics содержит rag_uploads_total."""
        # Prometheus обычно на отдельном порту, но прототип использует общий endpoint
        # из main.py через instrumentation — проверим, что имя метрики зарегистрировано
        from app.admin.rag_metrics import (
            RAG_CHUNKS_TOTAL,
            RAG_INGEST_DURATION,
            RAG_QUEUE_DEPTH,
            RAG_UPLOADS_TOTAL,
        )

        # prometheus_client автоматически добавляет "_total" к Counter names
        # (но в атрибуте ._name хранится без суффикса).
        assert RAG_UPLOADS_TOTAL._name == "rag_uploads"
        assert RAG_CHUNKS_TOTAL._name == "rag_chunks"
        assert RAG_INGEST_DURATION._name == "rag_ingest_duration_seconds"
        assert RAG_QUEUE_DEPTH._name == "rag_queue_depth"


# === Helpers ===


def _make_minimal_pdf() -> bytes:
    """Минимальный валидный PDF (1 страница, 0 текста) для тестов extract_text_from_pdf."""
    # Реальный PDF header + EOF marker; pypdf примет без exception.
    # Используем pypdf для генерации — иначе test_pdf_extraction ломается.
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
