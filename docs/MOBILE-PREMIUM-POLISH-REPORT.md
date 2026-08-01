# Mobile Premium Polish Report

Date: 2026-08-01
Branch: `mvp-rescue`

## Result

Mobile adaptation for the premium Neon Coast design is complete.

The app is now optimized for phone usage across the main pilot surfaces:

- `/login`
- `/subjects`
- `/subjects/[id]`
- `/topics/[id]`
- `/teacher/topics`
- `/parent/dashboard/[studentId]`

## What Changed

### Global Mobile System

- Added `mobile-scroll-safe` for lesson screens.
- Added mobile-specific CSS rules for:
  - `100dvh` behavior;
  - smaller hero radii;
  - smaller mobile title scale;
  - single-column chip navigation;
  - safe tap targets;
  - less visual noise from background grid.
- Changed premium shell from clipping overflow to only preventing horizontal overflow.

### Login

- Reduced hero title on phones.
- Changed login shell to `min-h-dvh`.
- Reduced padding/radius on phone.
- Kept large desktop cinematic layout.

### Subjects

- Reduced mobile hero padding/title.
- Subject grid uses one column on small phones and two columns from `sm`.
- Search remains full-width and touch-friendly.
- Cards keep premium style while avoiding cramped mobile layout.

### Subject Detail

- Reduced mobile hero padding/title.
- Topic deck header stacks on mobile.
- Topic cards stack content vertically on mobile instead of forcing a wide row.

### Lesson / Topic

- Lesson shell now uses `100dvh`-safe sizing.
- Main action buttons become full-width 44px+ tap targets on mobile.
- Chat message width increased on mobile for readability.
- Chat input and send button stack vertically on mobile.
- Added safe-area bottom padding for phone browsers.

### Teacher Readiness

- Desktop keeps table layout.
- Mobile gets a dedicated card layout instead of horizontal table scrolling.
- Readiness cards show core stats and status pills with comfortable touch targets.

## Verification

Local:

- Frontend typecheck: passed
- Frontend build: passed
- MVP E2E: `2 passed`

## Known Limitations

- Some secondary admin/material utility screens still use older non-premium layout.
- The main student/teacher/parent pilot surfaces are mobile-polished.
