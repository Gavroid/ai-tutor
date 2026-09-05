"""Sprint 3.38: CSP violation report endpoint.

Принимает JSON от браузера при violation, логирует в logger с severity=warning.
Не возвращает наружу никаких данных (только 204) чтобы endpoint не стал
источником шумных 200 OK для случайных ботов.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/csp-report", tags=["security"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def csp_report(request: Request) -> Response:
    """Принимает CSP violation report от браузера.

    Browser POSTs JSON в формате:
    {
      "csp-report": {
        "document-uri": "https://example.com/page",
        "violated-directive": "script-src 'self'",
        "blocked-uri": "https://evil.com/x.js",
        "original-policy": "default-src 'self'; ...",
        ...
      }
    }
    """
    try:
        report = await request.json()
        # Логируем полный report — помогает при security review.
        logger.warning(
            "CSP violation: %s",
            report,
        )
    except Exception as e:
        logger.warning("CSP report parse error: %s", e)
    # 204 No Content — не возвращаем ничего (минимизация attack surface).
    return Response(status_code=status.HTTP_204_NO_CONTENT)
