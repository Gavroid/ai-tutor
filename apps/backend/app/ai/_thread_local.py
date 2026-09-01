"""Thread-local storage for AI service per-request state (S3.1).

Why: AIService is a singleton, but in concurrent TestClient / FastAPI
environments, multiple requests run in different threads. To pass
per-request state (e.g. multi-explain style) without changing the
singleton's public signature, we use threading.local().

Pattern:
  from app.ai import _thread_local
  _thread_local.explain_style = "simpler"
  ...  # AIService reads it
"""
from __future__ import annotations

import threading

_thread_local = threading.local()