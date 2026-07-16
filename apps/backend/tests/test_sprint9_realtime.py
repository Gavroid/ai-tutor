"""Sprint 9.3: real-time WS для админа.

Sprint 3.5.1 — DEAD CODE TEST FILE
==================================
Real-time /admin WebSocket: endpoint есть (/api/v1/admin/ws), код есть
(app/admin/realtime.py), тесты проходят. НО UI-ссылка скрыта в Pilot
Core Stage 1 Phase 5 (не показывается в /admin). single-worker OK,
но при multi-worker не работает (нет Redis pub/sub).

Для 1 пользователя (ты как admin) — это overkill. Реактивировать если
решишь подключить multi-worker (Sprint 6.3) или выставить UI.
"""
from __future__ import annotations

import json
import time

import pytest

pytestmark = pytest.mark.skip(
    reason="Sprint 3.5.1: real-time WS UI скрыт (Pilot Phase 5), "
           "single-worker OK. Реактивировать при multi-worker или показе UI."
)

import pytest
from fastapi.testclient import TestClient

from app.admin.realtime import _metrics_snapshot, _system_health
from app.auth.security import create_access_token
from app.db.session import Base, SessionLocal, engine
from app.main import app
from app.users import service as user_service
from app.users.schemas import UserCreate


@pytest.fixture()
def admin_user():
    Base.metadata.drop_all(engine)
    engine.dispose()
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        admin = user_service.register_user(
            db,
            UserCreate(
                email="admin-rt@example.com",
                password="strongpass1",
                display_name="Админ",
                role="admin",
            ),
        )
        db.commit()
        token, _ = create_access_token(admin)
        return {"admin_id": admin.id, "token": token}
    finally:
        db.close()


class TestMetricsSnapshot:
    """_metrics_snapshot не падает при отсутствии любой части."""

    def test_snapshot_returns_expected_shape(self):
        snap = _metrics_snapshot()
        assert "ts" in snap
        assert "ai_modes" in snap
        assert "ai_tokens" in snap
        assert "http_total" in snap
        assert "system" in snap
        # system содержит ожидаемые поля
        assert "db" in snap["system"]
        assert "redis" in snap["system"]

    def test_ai_modes_is_dict(self):
        snap = _metrics_snapshot()
        assert isinstance(snap["ai_modes"], dict)

    def test_http_total_buckets(self):
        snap = _metrics_snapshot()
        http = snap["http_total"]
        assert "2xx" in http
        assert "4xx" in http
        assert "5xx" in http


class TestSystemHealth:
    def test_safe_when_docker_missing(self):
        """Если docker недоступен — вернёт unknown (не упадёт)."""
        # На CI docker может отсутствовать; функция не должна ронять
        result = _system_health()
        assert "db" in result
        assert "redis" in result
        assert "backend" in result


class TestAdminWS:
    """WS endpoint: 1008 при невалидном токене/не admin."""

    def test_no_token_rejected(self):
        c = TestClient(app)
        with pytest.raises(Exception):
            with c.websocket_connect("/api/v1/admin/ws"):
                pass

    def test_invalid_token_rejected(self):
        c = TestClient(app)
        with pytest.raises(Exception):
            with c.websocket_connect("/api/v1/admin/ws?token=INVALID_TOKEN"):
                pass

    def test_non_admin_token_rejected(self):
        Base.metadata.drop_all(engine)
        engine.dispose()
        Base.metadata.create_all(engine)
        db = SessionLocal()
        try:
            student = user_service.register_user(
                db,
                UserCreate(
                    email="stu@example.com",
                    password="strongpass1",
                    display_name="Студент",
                    role="student",
                    grade=7,
                ),
            )
            db.commit()
            student_token, _ = create_access_token(student)
        finally:
            db.close()

        c = TestClient(app)
        with pytest.raises(Exception):
            with c.websocket_connect(f"/api/v1/admin/ws?token={student_token}"):
                pass
