"""Тесты OCR (Этап 10)."""
from __future__ import annotations

import io
import os

os.environ["APP_SECRET_KEY"] = "test-secret-key-for-pytest-only-1234567890"
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["AI_API_KEY"] = "mock-key-for-tests"

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine, get_db
from app.main import app
from app.subjects.scripts_seed_runner import seed_for_tests
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)

    s = SessionLocal()
    try:
        user_service.register_user(
            s,
            UserCreate(
                email="teacher@example.com",
                password="strongpass1",
                display_name="Учитель",
                role="teacher",
            ),
            allow_private_bypass=True,
        )
        seed_for_tests(s, reset=False)
    finally:
        s.close()

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


def _login(c: TestClient) -> str:
    return c.post(
        "/api/v1/auth/login",
        json={"email": "teacher@example.com", "password": "strongpass1"},
    ).json()["access_token"]


def _first_algebra_topic_id() -> int:
    s = SessionLocal()
    try:
        from app.subjects import models as subj_models

        algebra = s.scalar(
            __import__("sqlalchemy").select(subj_models.Subject).where(subj_models.Subject.code == "algebra")
        )
        topic = s.scalar(
            __import__("sqlalchemy").select(subj_models.Topic)
            .join(subj_models.Section)
            .where(subj_models.Section.subject_id == algebra.id)
            .limit(1)
        )
        return topic.id
    finally:
        s.close()


def test_upload_image_accepted(client):
    """PNG принимается (если pytesseract или fallback)."""
    teacher_token = _login(client)
    tid = _first_algebra_topic_id()
    # Минимальный валидный PNG (1x1 пиксель)
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63f8cf000000030001005e9d6b800000000049454e44ae426082"
    )
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid, "ocr_langs": "rus+eng"},
        files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == "test.png"
    # Контент — либо OCR-результат, либо fallback-сообщение
    assert "content" in body or body.get("source")


def test_upload_image_without_ocr_langs(client):
    """OCR-langs опциональны — без них используется default (rus+eng)."""
    teacher_token = _login(client)
    tid = _first_algebra_topic_id()
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63f8cf000000030001005e9d6b800000000049454e44ae426082"
    )
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid},
        files={"file": ("test2.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert r.status_code == 200


def test_reject_unsupported_image_format(client):
    """GIF не в списке."""
    teacher_token = _login(client)
    tid = _first_algebra_topic_id()
    fake_gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid},
        files={"file": ("test.gif", io.BytesIO(fake_gif), "image/gif")},
    )
    assert r.status_code == 400


def test_jpeg_accepted(client):
    """JPEG тоже в списке."""
    teacher_token = _login(client)
    tid = _first_algebra_topic_id()
    # Минимальный JPEG (SOI + APP0 + EOI)
    jpeg_bytes = bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb0043000806060706050806070707070908")
    r = client.post(
        "/api/v1/materials/upload",
        headers={"Authorization": f"Bearer {teacher_token}"},
        data={"topic_id": tid, "ocr_langs": "eng"},
        files={"file": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
    )
    assert r.status_code == 200