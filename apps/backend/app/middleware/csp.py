"""Sprint 3.38: Content-Security-Policy middleware для FastAPI.

ВНИМАНИЕ: по умолчанию CSP в **report-only mode** — нарушения логируются
но НЕ блокируют контент. Это безопаснее для staged rollout.

Для enforce mode установите `csp_enforce=True` в config или env
`CSP_ENFORCE=true`. После того как убедитесь что нет violations в
логах — переключайтесь.

Директивы CSP:
- default-src 'self' — только same-origin по умолчанию
- script-src 'self' 'unsafe-inline' — Next.js требует inline scripts
  (hydration). 'unsafe-inline' можно убрать если настроите nonce-based
  scripts (требует изменения Next.js build config, см. Sprint 3.38a).
- style-src 'self' 'unsafe-inline' — Tailwind/Next.js inline styles
- img-src 'self' data: https: — Next.js Image с внешних CDN
- font-src 'self' data: — локальные шрифты + data: URIs
- connect-src 'self' https: — API calls к проде + analytics
- frame-ancestors 'none' — анти-clickjacking
- form-action 'self' — формы только same-origin
- base-uri 'self' — защита от <base> hijacking
- report-uri /api/v1/csp-report — endpoint для приёма violation reports

NOTE: 'unsafe-inline' для script-src — это компромисс для Next.js.
В Этапе 3.38a запланировано убрать через nonce-based CSP.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# CSP directives. 'self' = same-origin. 'unsafe-inline' — для Next.js.
# Чтобы убрать — нужен nonce-based CSP (Sprint 3.38a).
_CSP_DIRECTIVES = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https:",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "report-uri /api/v1/csp-report",
]


class CSPMiddleware(BaseHTTPMiddleware):
    """Добавляет Content-Security-Policy header ко всем ответам.

    По умолчанию report-only mode (Content-Security-Policy-Report-Only).
    Чтобы enforce — установите `enforce=True` через инициализатор.
    """

    def __init__(self, app: Any, *, enforce: bool = False) -> None:
        super().__init__(app)
        self.enforce = enforce
        # В report-only mode пишем в header `Content-Security-Policy-Report-Only`,
        # браузер только репортит violations но не блокирует.
        # В enforce mode пишем в `Content-Security-Policy` — браузер блокирует.
        self.header_name = (
            "Content-Security-Policy" if enforce else "Content-Security-Policy-Report-Only"
        )
        self.csp_value = "; ".join(_CSP_DIRECTIVES)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers[self.header_name] = self.csp_value
        return response
