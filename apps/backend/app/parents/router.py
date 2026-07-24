"""Роутер родительского кабинета.

Sprint 1.1: все endpoints защищены require_parent()/require_student().
Sprint 32: 2FA TOTP endpoints для parent.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin import service as audit_service
from app.common.deps import User, require_parent, require_student
from app.db.session import get_db
from app.parents import schemas, service
from app.users import twofa

router = APIRouter(prefix="/api/v1/parents", tags=["parents"])


@router.post("/invite", response_model=schemas.InviteOut)
def create_invite(
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    code = service.create_invite_for_parent(db, current)
    return schemas.InviteOut(code=code)


@router.get("/children", response_model=list[schemas.LinkedStudent])
def list_children(
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    return service.list_linked_students(db, current)


@router.get("/children/{student_id}", response_model=schemas.ChildOverview)
def child_overview(
    student_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    overview = service.child_overview(db, current, student_id)
    if overview is None:
        raise HTTPException(404, "Ребёнок не привязан или не найден")
    return overview


@router.get("/students/{student_id}/dashboard", response_model=schemas.ChildDashboard)
def child_dashboard(
    student_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    """Sprint 3.1 — расширенный дашборд: mastery по предметам, серии, типичные ошибки.

    404 если student не привязан к этому parent.
    """
    dash = service.child_dashboard(db, current, student_id)
    if dash is None:
        raise HTTPException(404, "Ребёнок не привязан или не найден")
    return dash


@router.get("/students/{student_id}/dashboard.pdf")
def child_dashboard_pdf(
    student_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    """Sprint 3.3 — экспорт дашборда в HTML (PDF-ready).

    Возвращает HTML, который можно распечатать/сохранить как PDF через браузер.
    Не тянет тяжёлые зависимости (weasyprint/reportlab) — обходимся HTML.
    """
    from fastapi.responses import HTMLResponse

    dash = service.child_dashboard(db, current, student_id)
    if dash is None:
        raise HTTPException(404, "Ребёнок не привязан или не найден")
    html = _render_dashboard_html(dash)
    return HTMLResponse(content=html)


def _render_dashboard_html(dash: schemas.ChildDashboard) -> str:
    """Простой HTML-шаблон для печати."""
    s = dash.student
    rows_subjects = "".join(
        f"<tr><td>{sm.subject_name}</td>"
        f"<td>{sm.topics_attempted}/{sm.topics_total}</td>"
        f"<td>{sm.avg_mastery * 100:.1f}%</td>"
        f"<td>{sm.accuracy * 100:.1f}%</td></tr>"
        for sm in dash.subject_mastery
    )
    rows_weak = "".join(
        f"<tr><td>{w.topic_name}</td><td>{w.subject_name}</td>"
        f"<td>{w.mastery * 100:.1f}%</td></tr>"
        for w in dash.weak_topics
    )
    rows_mistakes = "".join(
        f"<tr><td>{m.mistake_type}</td><td>{m.topic_name}</td>"
        f"<td>{m.count}</td><td>{m.last_seen}</td></tr>"
        for m in dash.top_mistakes
    )
    streak = dash.streak
    ts = dash.time_stats
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Отчёт по {s.display_name}</title>
<style>
body {{ font-family: sans-serif; margin: 24px; color: #222; }}
h1 {{ border-bottom: 2px solid #444; padding-bottom: 8px; }}
h2 {{ margin-top: 24px; color: #444; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
th {{ background: #f5f5f5; }}
.kpi {{ display: inline-block; padding: 8px 16px; margin: 4px;
  border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }}
.kpi b {{ font-size: 18px; display: block; }}
.privacy {{ margin-top: 32px; padding: 12px; background: #fff8dc;
  border: 1px solid #e6d36e; border-radius: 6px; font-size: 13px; }}
small {{ color: #888; }}
</style>
</head>
<body>
<h1>Отчёт по ученику: {s.display_name}</h1>
<p><small>{dash.generated_at.isoformat()}</small></p>

<h2>Сводка</h2>
<div class="kpi"><b>{dash.total_attempts}</b>попыток всего</div>
<div class="kpi"><b>{dash.accuracy * 100:.1f}%</b>точность</div>
<div class="kpi"><b>{dash.average_mastery * 100:.1f}%</b>средний mastery</div>
<div class="kpi"><b>{streak.current_streak_days}</b>текущая серия</div>
<div class="kpi"><b>{streak.longest_streak_days}</b>лучшая серия</div>
<div class="kpi"><b>{dash.due_for_review_count}</b>к повторению</div>

<h2>Активность</h2>
<p>Последние 7 дней: <b>{ts.last_7_days}</b> попыток.
   30 дней: <b>{ts.last_30_days}</b>.
   В среднем {ts.avg_per_active_day} попыток / активный день.</p>

<h2>По предметам</h2>
<table>
<tr><th>Предмет</th><th>Тем пройдено</th><th>Mastery</th><th>Точность</th></tr>
{rows_subjects or "<tr><td colspan=4>Нет данных</td></tr>"}
</table>

<h2>Слабые темы (mastery &lt; 60%)</h2>
<table>
<tr><th>Тема</th><th>Предмет</th><th>Mastery</th></tr>
{rows_weak or "<tr><td colspan=3>Нет слабых тем</td></tr>"}
</table>

<h2>Типичные ошибки</h2>
<table>
<tr><th>Тип</th><th>Тема</th><th>Кол-во</th><th>Последний раз</th></tr>
{rows_mistakes or "<tr><td colspan=4>Нет типичных ошибок</td></tr>"}
</table>

<div class="privacy">
🔒 {dash.privacy_note}
</div>
</body>
</html>"""


# Эндпоинт для РЕБЁНКА — привязать себя к родителю
student_router = APIRouter(prefix="/api/v1/students", tags=["students"])

# === Sprint 32: 2FA TOTP endpoints ===

class TwoFAEnableOut(BaseModel):
    """Sprint 32: ответ при enable 2FA."""
    secret: str
    provisioning_uri: str
    backup_codes: list[str]


class TwoFAVerifyIn(BaseModel):
    """Sprint 32: TOTP код или backup code для подтверждения."""
    code: str = Field(min_length=6, max_length=12)


class TwoFAStatusOut(BaseModel):
    """Sprint 32: статус 2FA для parent."""
    enabled: bool
    last_used_at: str | None = None
    backup_codes_remaining: int = 0


@router.post("/2fa/enable", response_model=TwoFAEnableOut)
def enable_2fa(
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    """Sprint 32: enable 2FA TOTP для parent.

    Возвращает:
    - secret (base32, для ручного ввода в Google Authenticator)
    - provisioning_uri (otpauth:// для QR-code)
    - backup_codes (8 одноразовых кодов, показываются ОДИН раз!)

    Sprint 32 NOTE: secret и codes возвращаются только при enable.
    Пере-enable требует disable сначала.
    """
    try:
        result = twofa.enable_2fa(current.id, current.email)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    audit_service.record(
        db,
        user=current,
        action="2fa.enable",
        entity="user",
        entity_id=str(current.id),
        details={"method": "totp"},
    )

    return TwoFAEnableOut(**result)


@router.post("/2fa/disable", status_code=204)
def disable_2fa(
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    """Sprint 32: disable 2FA.

    Sprint 32 NOTE: требует fresh password для подтверждения (TODO Sprint 33+).
    Сейчас требует только authenticated parent.
    """
    if not twofa.has_2fa_enabled(current.id):
        raise HTTPException(400, "2FA не включена")

    twofa.disable_2fa(current.id)

    audit_service.record(
        db,
        user=current,
        action="2fa.disable",
        entity="user",
        entity_id=str(current.id),
        details={"method": "self"},
    )


@router.get("/2fa/status", response_model=TwoFAStatusOut)
def get_2fa_status(
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    """Sprint 32: статус 2FA (enabled, last_used_at, backup_codes_remaining)."""
    from app.db.session import engine as _engine
    from sqlalchemy import text

    if not twofa.has_2fa_enabled(current.id):
        return TwoFAStatusOut(enabled=False)

    with _engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT last_used_at, backup_codes_json "
                "FROM parent_2fa WHERE parent_id = :pid"
            ),
            {"pid": current.id},
        ).fetchone()

    import json as _json
    backup_codes = _json.loads(row[1]) if row else []
    last_used = row[0].isoformat() if row and row[0] else None

    return TwoFAStatusOut(
        enabled=True,
        last_used_at=last_used,
        backup_codes_remaining=len(backup_codes),
    )


@router.post("/2fa/verify", response_model=schemas.ChildDashboard)
def verify_2fa(
    payload: TwoFAVerifyIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_parent()),
):
    """Sprint 32: standalone verify (для UI проверки введённого кода).

    Используется при enable: после QR-code сканирования родитель вводит
    6-значный TOTP и проверяет что Authenticator работает.
    """
    import json as _json
    from app.db.session import engine as _engine
    from sqlalchemy import text

    if not twofa.has_2fa_enabled(current.id):
        raise HTTPException(400, "2FA не включена")

    # Расшифровать secret
    with _engine.connect() as conn:
        encrypted = conn.execute(
            text("SELECT secret_encrypted FROM parent_2fa WHERE parent_id = :pid"),
            {"pid": current.id},
        ).scalar()

    if encrypted is None:
        raise HTTPException(400, "2FA секрет не найден")

    secret = twofa.decrypt_secret(encrypted)
    code = payload.code.strip()

    valid = False
    if len(code) == 6 and code.isdigit():
        valid = twofa.verify_totp(secret, code)
    else:
        # Backup code (12 hex chars)
        valid = twofa.verify_backup_code(current.id, code)

    if not valid:
        raise HTTPException(401, "Неверный код")

    return {"ok": True, "message": "Код верный"}


@student_router.post("/link-parent")
def link_parent(
    payload: schemas.AcceptInviteIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_student()),
):
    try:
        ok = service.accept_invite(db, current, payload.code)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not ok:
        raise HTTPException(400, "Не удалось привязаться")

    audit_service.record(
        db,
        user=current,
        action="parent.link",
        entity="student",
        entity_id=str(current.id),
        details={"invite_code": payload.code[:8] + "***"},
    )
    return {"ok": True, "message": "Родитель привязан"}
