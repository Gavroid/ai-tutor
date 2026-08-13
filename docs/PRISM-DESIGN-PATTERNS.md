# AI-Tutor Prism Design Patterns

_Last updated: 2026-08-13_
_Production marker at latest design capture: `bf0b765`_

This document is the source-of-truth for the MVP visual patterns after the admin/teacher polish pass. Use it before changing any dashboard, console, teacher, admin, or lesson page.

## 1. Product Visual Direction

AI-Tutor uses a dark Prism/Split interface:

- deep navy / near-black base;
- subtle glass panels;
- restrained cyan, violet, pink, and warm orange glow;
- light grid texture only as background structure;
- no legacy white Tailwind cards;
- no aggressive green fills;
- neutral buttons by default, color only on hover or active emphasis.

The target feel is close to the main lesson pages (`/topics/[id]`) and subjects pages (`/subjects`): calm, dark, premium, and readable.

## 2. Core Page Shell

Use this structure for major app pages:

```tsx
<main className="prism-shell ... min-h-dvh">
  <Header user={user} backHref="/subjects" title="..." />
  <section className="py-3 sm:py-5">
    <div className="prism-frame">
      <div className="prism-layer p-5 lg:p-10">
        {/* page content */}
      </div>
    </div>
  </section>
</main>
```

Rules:

- `Header` is a top panel outside the content frame.
- Do not nest semantic page `<header>` blocks inside `prism-frame`; use `<section>`/`div` content headers.
- Main content starts below the top panel.
- Do not reintroduce separate light containers around admin/teacher sections.
- Do not add `← На главную` links inside console content when `Header` already provides navigation.

## 3. Main Student/Lesson Pages

Canonical examples:

- `/subjects`
- `/topics/[id]`
- `/diagnostic`
- `/link-parent`

Patterns:

- dark background with muted cyan/violet/pink glow;
- rounded panels with thin translucent borders;
- section labels with small blue accent bars;
- buttons are neutral gray/dark by default;
- hover may introduce cyan/violet/pink color;
- lesson pages use a stable split layout:
  - left lesson rail;
  - center tutor chat;
  - right practice panel.

Do not use admin-console overrides on student lesson pages.

## 4. Admin Console Pattern

Canonical route:

```text
/admin
```

All admin sections must be internal state tabs on the same URL:

- `Audit log`
- `Пользователи`
- `Статистика`
- `Инструменты`
- `Invites`
- `Realtime`

Rules:

- Browser URL remains `/admin` while switching tabs.
- Do not link visible tabs to `/admin/invites`, `/admin/realtime`, or `/admin?tab=...`.
- Legacy routes may exist for compatibility, but the visible admin nav should use state buttons.
- Use `console-pill` and `console-pill-active`, not `prism-pill`, for admin tab controls.
- Long tables/lists scroll inside the panel; they must not resize the outer `prism-frame`.
- `admin-content-zone` is the stable background area for tab content.
- The frame/background should not change when moving between short and long tabs.

Expected nav pattern:

```tsx
<Tab active={tab === "audit"} onClick={() => setTab("audit")}>Audit log</Tab>
<Tab active={tab === "users"} onClick={() => setTab("users")}>Пользователи</Tab>
<Tab active={tab === "stats"} onClick={() => setTab("stats")}>Статистика</Tab>
<Tab active={tab === "tools"} onClick={() => setTab("tools")}>Инструменты</Tab>
<Tab active={tab === "invites"} onClick={() => setTab("invites")}>Invites</Tab>
<Tab active={tab === "realtime"} onClick={() => setTab("realtime")}>Realtime</Tab>
```

## 5. Teacher Console Pattern

Canonical route:

```text
/teacher
```

Patterns:

- One URL for the material library/filter surface.
- Do not show `← На главную` inside the content frame; navigation lives in `Header`.
- Use `console-pill` / `console-pill-active` for teacher filters.
- Use internal scrolling for long material lists.
- Empty states must keep the frame geometry stable and centered.
- Teacher/admin material cards use `prism-card prism-topic-card` for hover lift/glow.

Teacher filters:

- `Все`
- `Черновик`
- `AI сгенерировал`
- `Одобрено`
- `Опубликовано`

Rules:

- Switching filters must not shift the outer frame.
- Empty filter results must not collapse to a tiny card.
- Admin users may see more data than teacher users; layout must remain stable for both.

## 6. Button Rules

Default:

- neutral dark/gray fill;
- subtle border;
- no loud color fill;
- readable white/muted text.

Active:

- keep neutral fill;
- use amber/gold border and text for selected tab/filter;
- do not use black, green, or full gradient as permanent active background.

Hover:

- all admin/teacher buttons use one shared cyan/violet/pink gradient hover treatment;
- white text on hover;
- consistent glow and border.

Use:

```css
.console-pill
.console-pill-active
.prism-action
```

Avoid using `.prism-pill` for admin/teacher tab controls because it has legacy cascade conflicts.

## 7. Background Rules

Keep admin/teacher closer to original site palette:

- dark navy/black base;
- subdued glow, not bright magenta/cyan panels;
- no large green background blocks;
- no white fills;
- no background jump between tabs.

Important implementation notes:

- Console frame geometry is fixed on desktop.
- Long data scrolls inside the content area, not the whole page frame.
- `prism-frame::after` glow is fixed to viewport to avoid gradient drift on long tables.
- `admin-content-zone` gives admin tabs one stable background surface.

## 8. Cards, Tables, and Empty States

Cards:

- use dark translucent surfaces;
- thin `var(--prism-line)` borders;
- rounded 24-30px corners;
- optional subtle inset highlight.

Tables:

- dark transparent table backgrounds;
- no white `thead`/`tbody`/`tr` fills;
- row borders use `var(--prism-line)`;
- dense but readable spacing.

Empty states:

- must occupy meaningful vertical space;
- center the text/action;
- must not collapse the frame height.

## 9. Regression Checklist

Before declaring a visual change done:

1. Run frontend gates:

```bash
cd /root/workspace/ai-tutor/apps/frontend
npm run typecheck
npm run build
```

2. Deploy frontend and verify:

```bash
curl -sk -w '\nHTTP=%{http_code}\n' https://192.168.1.86/ready
ssh -i /root/.ssh/id_ed25519_kirill_ai -o BatchMode=yes root@192.168.1.86 'cat /opt/ai-tutor/.mvp-rescue-commit; cd /opt/ai-tutor/deploy && docker compose ps frontend'
```

3. Playwright audit on public domain:

- `/admin`: click every tab; URL must stay `/admin`.
- `/teacher`: click every filter; URL must stay `/teacher`.
- Verify:
  - no white panels;
  - no horizontal overflow;
  - outer frame geometry stable;
  - active tab class is `console-pill-active`;
  - long content scrolls inside the panel.

4. Always verify against:

```text
https://school.431a.ru
```

not only LAN IP.

## 10. Known Good Backup After Design Pass

Fresh backup after final palette pass:

```text
manifest: /opt/ai-tutor/deploy/backup/_out/manifest-20260812T162036Z.md5
DB:       /opt/ai-tutor/deploy/backup/_out/db-20260812T162036Z.sql.gz
uploads:  /opt/ai-tutor/deploy/backup/_out/uploads-20260812T162036Z.tar.gz
```

Offsite verification:

```text
OFFSITE OK: hash verified manifest-20260812T162036Z.md5
hash: 2e73706b2ea9f5f784dea4d111fc84ee
uploaded: 27 files
retention deleted: 3 old files
total on SMB: 199
```

Production marker at backup:

```text
19a8d52
```

## 10. Mobile Chat Reading Pattern

Canonical route:

```text
/topics/[id]
```

Rules:

- Mobile lesson uses three tabs: `Чат`, `Урок`, `Практика`.
- `Объяснить` switches to `Чат` after generating an answer.
- `Практика` switches to `Практика` after generating an exercise.
- Assistant answers use `SafeMarkdown`; raw markdown tables must render as responsive tables, not literal `| ... |` text.
- AI answer cards must have readable spacing:
  - paragraphs separated;
  - lists have visible markers and spacing;
  - tables are horizontally scrollable inside the bubble;
  - follow-up chips wrap into a single column on mobile;
  - decorative orbs/chips never overflow the viewport.
- Mobile QA should verify `overflow = 0` on `/topics/[id]` for chat, lesson, and practice panels.

## 11. Current Realtime Pattern

Admin Realtime is not a live stream in the MVP UI.

Rules:

- It displays one fixed snapshot when opening the tab.
- Values change only on manual `Обновить`.
- Counters are cumulative since backend start.
- Backend RAM is cgroup-based MiB; show percent only if a real cgroup memory limit exists.
- Do not reintroduce 3-second auto-polling unless labels and expected counter movement are redesigned.
- Keep backend `workers=1` until Prometheus multiprocess mode is implemented.

