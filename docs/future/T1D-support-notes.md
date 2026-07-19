# Sprint 11.5 — T1D-friendly UX notes

## Что сделано в этом Sprint 11.5
- **font-size 17px** (было 16px) — лучше читается при гипо/гипер
- **line-height 1.55** — длинные AI-ответы комфортнее
- **focus-visible 3px solid ring** — крупная обводка для keyboard users
- **skip-link "Перейти к содержимому"** — для скрин-ридеров и keyboard nav
- **prefers-reduced-motion** — уважает настройки ОС (важно для T1D эпизодов)
- **EmptyState компонент** — позитивные сообщения в empty states (без давления "у тебя нет результатов")
- **Skeleton вместо "Загрузка..."** — нет скачков layout, нет ощущения зависания
- **per-role landing page** — родитель сразу попадает на /parents (не на /subjects)

## T1D UX considerations (для следующих спринтов)
- **Glucose-aware session length warning**: если урок затянулся (>20 мин) — мягкий
  prompt "Ты давно занимаешься, сделай перерыв".
- **Pause button** ("Сделать паузу / у меня гипо"): останавливает время сессии
  и НЕ считает streak как прерванный. T1D-friendly.
- **Calm color palette**: текущая палитра cool (sky + emerald) — не раздражает.
  Избегать ярко-красного кроме реальных ошибок.
- **Larger hit zones для T1D при слабой моторике** (>50px вместо 36px minimum).
- **Quick-logout / quick-pause**: floating action button в углу (как ThemeToggle сейчас).
- **Audio cue on completion**: для детей которые могут не смотреть на экран.

## Sprint 11.5 commit
- apps/frontend/app/globals.css: 17px font + focus-visible + skip-link
- apps/frontend/app/layout.tsx: skip-link в body
- apps/frontend/app/login/page.tsx: per-role redirect
- apps/frontend/components/EmptyState.tsx: компонент
- apps/frontend/components/Skeleton.tsx: компонент
- apps/frontend/app/parents/page.tsx: 3 empty states
- apps/frontend/app/student/badges/client.tsx: skeleton при loading
