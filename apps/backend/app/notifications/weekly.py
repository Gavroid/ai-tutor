"""Weekly summary для родителя (Sprint 9.1).

Генерирует HTML-текст сводки и отправляет через существующий `send_email`.
Запускается cron'ом раз в неделю (воскресенье 18:00 MSK).

Безопасно:
- Только агрегаты (никаких сырых диалогов с AI).
- Если для ученика нет данных — пропускаем.
- Если нет SMTP — dry-run.
- Если у родителя нет email — пропускаем.

Usage:
    from app.notifications.weekly import send_weekly_summary_for_parent
    from app.db.session import SessionLocal
    db = SessionLocal()
    send_weekly_summary_for_parent(db, parent_id=1)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users import models as user_models

logger = logging.getLogger(__name__)


def _aggregate_progress_for_student(db: Session, student_id: int, week_start: datetime) -> dict:
    """Агрегирует успехи ученика за неделю: попытки, mastery, mistakes, активные дни.

    Без PII и без сырых диалогов — только цифры.
    """
    from app.progress import models as prog_models

    week_end = week_start + timedelta(days=7)

    attempts = db.execute(
        select(prog_models.Attempt).where(
            prog_models.Attempt.user_id == student_id,
            prog_models.Attempt.created_at >= week_start,
            prog_models.Attempt.created_at < week_end,
        )
    ).scalars().all()

    correct = sum(1 for a in attempts if a.is_correct)
    total = len(attempts)
    accuracy = (correct / total * 100) if total else 0.0

    progress_rows = db.execute(
        select(prog_models.Progress).where(prog_models.Progress.user_id == student_id)
    ).scalars().all()

    mastery_avg = (
        sum(p.mastery_score for p in progress_rows) / len(progress_rows)
        if progress_rows
        else 0.0
    )

    active_days = len({a.created_at.date() for a in attempts})

    return {
        "attempts_total": total,
        "attempts_correct": correct,
        "accuracy_pct": round(accuracy, 1),
        "topics_in_progress": len(progress_rows),
        "mastery_avg_pct": round(mastery_avg * 100, 1),
        "active_days": active_days,
    }


def _render_html(student_name: str, week_label: str, agg: dict) -> str:
    """HTML-шаблон для письма (f-string, без Jinja2 для минимума зависимостей)."""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<title>Еженедельная сводка AI-репетитора</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; padding: 24px; background: #f7fafc; color: #1a202c; }}
  .wrap {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  h1 {{ font-size: 22px; margin: 0 0 8px; }}
  .subtitle {{ color: #718096; margin: 0 0 22px; font-size: 14px; }}
  .kpi {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0 24px; }}
  .kpi-card {{ background: #f7fafc; border-radius: 8px; padding: 12px 14px; }}
  .kpi-num {{ font-size: 24px; font-weight: 700; color: #2d3748; margin: 0 0 4px; }}
  .kpi-label {{ font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 0.04em; }}
  .footer {{ color: #a0aec0; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>📊 Сводка за {escape(week_label)}</h1>
    <p class="subtitle">Ученик: <b>{escape(student_name)}</b></p>

    <div class="kpi">
      <div class="kpi-card"><p class="kpi-num">{agg["attempts_total"]}</p><p class="kpi-label">Попыток за неделю</p></div>
      <div class="kpi-card"><p class="kpi-num">{agg["accuracy_pct"]}%</p><p class="kpi-label">Точность</p></div>
      <div class="kpi-card"><p class="kpi-num">{agg["active_days"]}</p><p class="kpi-label">Активных дней</p></div>
      <div class="kpi-card"><p class="kpi-num">{agg["mastery_avg_pct"]}%</p><p class="kpi-label">Среднее освоение</p></div>
    </div>

    <p>Всего в работе — {agg["topics_in_progress"]} тем. Молодец!</p>

    <div class="footer">
      Это автоматическое уведомление. Подробный дашборд: <i>/parent/dashboard/[id]</i>.
    </div>
  </div>
</body>
</html>"""


def send_weekly_summary_for_parent(
    db: Session,
    parent_id: int,
    *,
    week_start: datetime | None = None,
) -> int:
    """Отправить weekly summary всем детям данного родителя.

    Returns:
        Количество успешно отправленных писем.
    """
    from app.notifications.service import _send_via_smtp

    week_start = week_start or (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).replace(hour=0, minute=0, second=0, microsecond=0)
    week_label = week_start.strftime("%d.%m") + "—" + (week_start + timedelta(days=6)).strftime("%d.%m.%Y")

    parent = db.get(user_models.User, parent_id)
    if parent is None or parent.role != "parent" or not parent.email:
        logger.info("Parent %s: no email or wrong role — skip", parent_id)
        return 0

    # Найти детей через parent_student_links (Sprint 3 модель)
    from app.users.models import ParentStudentLink

    children_ids = db.execute(
        select(ParentStudentLink.student_id).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.status == "active",
        )
    ).scalars().all()
    if not children_ids:
        logger.info("Parent %s: no children — skip", parent_id)
        return 0

    children = db.execute(
        select(user_models.User).where(user_models.User.id.in_(children_ids))
    ).scalars().all()

    sent_count = 0
    smtp_url = __import__("os").environ.get("SMTP_URL", "").strip()
    for child in children:
        agg = _aggregate_progress_for_student(db, child.id, week_start)
        if agg["attempts_total"] == 0 and agg["topics_in_progress"] == 0:
            continue  # нет данных — пропускаем
        html = _render_html(child.display_name or "Ученик", week_label, agg)
        subject = f"[AI-репетитор] Сводка за {week_label}: {child.display_name or 'ученик'}"
        body = f"Сводка за {week_label}\n\n{agg}\n\nAI-репетитор"
        if smtp_url:
            try:
                # Best-effort — ошибки отправки не критичны (log + continue)
                __import__("asyncio").run(_send_via_smtp(smtp_url, parent.email, subject, body))
                sent_count += 1
            except Exception as e:
                logger.warning("SMTP send failed for parent %s: %s", parent_id, e)
        else:
            logger.info("[DRY-RUN weekly summary to %s]: %s", parent.email, html[:200])
            sent_count += 1

    return sent_count


def send_weekly_summary_for_all_parents(db: Session) -> int:
    """Cron-обёртка: для каждого parent отправляет summary."""
    parents = db.execute(
        select(user_models.User).where(user_models.User.role == "parent")
    ).scalars().all()
    total_sent = 0
    for p in parents:
        total_sent += send_weekly_summary_for_parent(db, p.id)
    return total_sent
