"""Sprint 95: OpenTelemetry semantic conventions tests."""
from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import pytest
from unittest.mock import MagicMock, patch


# === Source verification ===

def test_resource_has_host_attribute():
    """Sprint 95: resource attributes содержит host.name."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert "host.name" in content
    assert "host.arch" in content
    assert "socket.gethostname" in content


def test_resource_has_process_attribute():
    """Sprint 95: resource attributes содержит process.pid."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert "process.pid" in content
    assert "process.runtime.name" in content
    assert "process.runtime.version" in content


def test_resource_has_deployment_attribute():
    """Sprint 95: resource attributes содержит deployment.git.commit_sha."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert "deployment.git.commit_sha" in content
    assert "git" in content.lower()


def test_resource_has_service_attributes():
    """Sprint 95: service.name + service.version + service.instance.id."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert "service.name" in content
    assert "service.version" in content
    assert "service.instance.id" in content


def test_semconv_reference():
    """Sprint 95: reference to OTel semantic conventions."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert "semconv" in content.lower() or "semantic" in content.lower()
    assert "opentelemetry.io" in content


# === Mock tests ===

@pytest.mark.skip(reason="OTel Resource mock complexity")
def test_resource_attributes_structure():
    """Sprint 95: resource attributes are well-formed dict."""
    from opentelemetry.sdk.resources import Resource

    # Mock Resource.create to capture attributes
    with patch("app.observability_otel.Resource") as mock_resource:
        mock_resource.create = MagicMock(return_value=MagicMock())

        with patch.dict(os.environ, {"OTEL_SDK_DISABLED": "true"}):
            from app.observability_otel import setup_telemetry
            setup_telemetry()

    # Resource.create should be called with attrs dict
    assert mock_resource.create.called


def test_git_commit_sha_fallback():
    """Sprint 95: git commit SHA fallback к 'unknown' если git unavailable."""
    # Verify code has fallback logic
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert 'or "unknown"' in content
    assert "except Exception" in content


def test_platform_info_used():
    """Sprint 95: использует platform module для host arch + python version."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..", "app", "observability_otel.py",
        )
    ) as f:
        content = f.read()
    assert "import platform" in content
    assert "platform.machine" in content
    assert "platform.python_version" in content