"""Sprint 10.3: API v2 каркас."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestV2Health:
    """/api/v2/health показывает, что v2 namespace жив."""

    def test_v2_health_ok(self):
        c = TestClient(app)
        r = c.get("/api/v2/health")
        assert r.status_code == 200
        body = r.json()
        assert body["v2"] == "ok"
        assert "version" in body

    def test_v2_info_returns_migration_state(self):
        c = TestClient(app)
        r = c.get("/api/v2/info")
        assert r.status_code == 200
        body = r.json()
        assert "v2_namespace" in body
        assert "migrated_from_v1" in body
        assert isinstance(body["migrated_from_v1"], list)


class TestV2CoexistsWithV1:
    """v1 endpoints НЕ затронуты (обратная совместимость)."""

    def test_v1_health_still_works(self):
        c = TestClient(app)
        r = c.get("/health")
        assert r.status_code == 200

    def test_v1_openapi_path_still_present(self):
        c = TestClient(app)
        r = c.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        # v1 корневые paths существуют
        assert "/api/v1/auth/login" in paths or "/api/v1/subjects" in paths
        # v2 корневые path существуют
        assert "/api/v2/health" in paths
        assert "/api/v2/info" in paths
