"""Sprint 98: Service Worker / PWA tests."""

from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# Sprint 98: resolve paths to frontend from this test file.
import os as _os
import re

import pytest

TEST_DIR = _os.path.dirname(_os.path.abspath(__file__))
REPO_ROOT = _os.path.abspath(_os.path.join(TEST_DIR, "..", "..", ".."))
FRONTEND_DIR = _os.path.join(REPO_ROOT, "apps", "frontend")
SW_PATH = _os.path.join(FRONTEND_DIR, "public", "sw.js")
OFFLINE_PATH = _os.path.join(FRONTEND_DIR, "app", "offline", "page.tsx")
LAYOUT_PATH = _os.path.join(FRONTEND_DIR, "app", "layout.tsx")
MANIFEST_PATH = _os.path.join(FRONTEND_DIR, "public", "manifest.json")


# === Service Worker file tests ===


def test_sw_js_exists():
    """Sprint 98: public/sw.js существует."""
    sw_path = SW_PATH
    assert os.path.exists(sw_path), "sw.js должен быть в public/"


def test_sw_js_has_install_listener():
    """Sprint 98: sw.js имеет install event listener."""
    with open(SW_PATH) as f:
        content = f.read()
    assert 'addEventListener("install"' in content


def test_sw_js_has_activate_listener():
    """Sprint 98: sw.js имеет activate event listener."""
    with open(SW_PATH) as f:
        content = f.read()
    assert 'addEventListener("activate"' in content


def test_sw_js_has_fetch_listener():
    """Sprint 98: sw.js имеет fetch event listener."""
    with open(SW_PATH) as f:
        content = f.read()
    assert 'addEventListener("fetch"' in content


def test_sw_js_caches_app_shell():
    """Sprint 98: sw.js caches /offline + /manifest.json + /icon.svg."""
    with open(SW_PATH) as f:
        content = f.read()
    assert "/offline" in content
    assert "/manifest.json" in content
    assert "/icon.svg" in content


def test_sw_js_network_first_for_api():
    """Sprint 98: API запросы → network first."""
    with open(SW_PATH) as f:
        content = f.read()
    assert "/api/" in content
    assert "networkFirstStrategy" in content


def test_sw_js_cache_first_for_static():
    """Sprint 98: static assets → cache first."""
    with open(SW_PATH) as f:
        content = f.read()
    assert "cacheFirstStrategy" in content


def test_sw_js_version_constant():
    """Sprint 98: CACHE_VERSION constant для cache invalidation."""
    with open(SW_PATH) as f:
        content = f.read()
    # Pattern: const CACHE_VERSION = "...";
    assert re.search(r'const CACHE_VERSION\s*=\s*"[^"]+";', content)
    assert re.search(r"const CACHE_NAME\s*=", content)


def test_sw_js_cleans_old_caches():
    """Sprint 98: activate listener удаляет old caches."""
    with open(SW_PATH) as f:
        content = f.read()
    assert "caches.delete" in content


# === Offline page tests ===


def test_offline_page_exists():
    """Sprint 98: app/offline/page.tsx существует."""
    offline_path = OFFLINE_PATH
    assert os.path.exists(offline_path)


def test_offline_page_has_reload_button():
    """Sprint 98: offline page имеет reload button."""
    with open(OFFLINE_PATH) as f:
        content = f.read()
    assert "window.location.reload" in content


# === Layout integration tests ===


def test_layout_registers_service_worker():
    """Sprint 98: layout.tsx регистрирует service worker."""
    with open(LAYOUT_PATH) as f:
        content = f.read()
    assert "serviceWorker.register" in content
    assert "/sw.js" in content


def test_manifest_json_remains_valid():
    """Sprint 98: manifest.json не сломан (важно для PWA installability)."""
    import json

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    assert manifest["name"]
    assert manifest["short_name"]
    assert manifest["start_url"]
    assert "icons" in manifest
    assert len(manifest["icons"]) > 0
