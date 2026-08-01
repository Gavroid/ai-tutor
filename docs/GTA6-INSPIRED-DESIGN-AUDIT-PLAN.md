# GTA-6-Inspired Design Audit & Implementation Plan

Date: 2026-07-31
Project: AI-Tutor MVP

## Design Direction

Working name: **Neon Coast Learning**.

The reference is not a copy of GTA VI assets, logos, characters, or UI. The usable visual direction is:

- neon-soaked city night;
- pink/orange sunset gradients;
- deep violet/navy background;
- turquoise/cyan highlight lights;
- glass panels;
- warm tropical accent energy;
- high-contrast readable education UI.

## Current Design Audit

### Strengths

- Existing component system already exists: `Button`, `Card`, `Badge`, `Header`, `Avatar`, `Input`.
- CSS variables are centralized in `globals.css`.
- Tailwind config maps semantic tokens (`brand`, `surface`, `fg`, `border`).
- Accessibility basics exist: focus-visible, reduced-motion handling, high base font size.

### Problems

1. **Visual identity is generic.** Current palette is standard indigo/neutral SaaS and does not feel distinctive.
2. **Gradient CTA is broken.** `Button` uses `bg-aurora-via-brand-500-to-pink-500`, which is not a valid Tailwind class.
3. **Cards are too neutral.** The app looks like a default education dashboard, not a memorable product.
4. **Header lacks brand atmosphere.** It is functional but visually plain.
5. **Subject cards do not create emotional pull.** They need more cinematic color, depth and status hierarchy.
6. **Dark/light theming is inconsistent with the requested art direction.** The requested visual language should be dark-neon-first while preserving readability.
7. **Educational safety matters.** GTA-like style must not become aggressive, noisy, or distract from reading.

## Implementation Plan

### Pass 1 — Global Visual System

- Replace brand tokens with neon coast palette:
  - sunset pink;
  - magenta;
  - neon cyan;
  - warm orange;
  - deep ocean navy.
- Add background utilities:
  - `bg-vice-city`;
  - `bg-neon-grid`;
  - `neon-panel`;
  - `neon-text`;
  - `shadow-neon`.
- Make global page background cinematic but readable.
- Preserve 17px base font and reduced motion handling.

### Pass 2 — Core Components

- Update `Button`:
  - primary = magenta/pink neon gradient;
  - secondary = glass/dark surface;
  - outline = neon border;
  - gradient = fixed valid gradient.
- Update `Card`:
  - glass/elevated variants become neon panels;
  - interactive cards get glow/translate.
- Update `Badge`:
  - stronger neon colors;
  - preview/status badges remain readable.
- Update `Header`:
  - dark translucent glass bar;
  - subtle neon border;
  - user badge fits new style.

### Pass 3 — Key Screens

- `/subjects`:
  - hero panel becomes neon coast landing section;
  - subject cards become cinematic tiles.
- `/subjects/[id]`:
  - subject status notice becomes visually clear.
- `/topics/[id]`:
  - keep lesson readability, but update surrounding shell and cards.
- `/parent/dashboard/[studentId]`:
  - recommendations become premium neon cards.
- `/teacher/topics` and `/teacher/topics/[id]`:
  - preserve table readability; add controlled neon accents only.

### Audit Passes After Implementation

1. **Audit 1 — Build/Token Audit**
   - TypeScript/build must pass.
   - No invalid Tailwind class names from the new design.
   - No unreadable foreground/background combinations in obvious components.

2. **Audit 2 — UX Readability Audit**
   - Lesson content remains readable.
   - Practice card remains calm and clear.
   - Warning/error/success colors remain semantically obvious.

3. **Audit 3 — MVP Flow Audit**
   - Student E2E still passes.
   - Teacher/parent/admin routes still build.
   - Final smoke ready for manual QA.

## Out of Scope For This Pass

- No copyrighted GTA assets.
- No logos/characters/posters from Rockstar.
- No major layout rewrite of every screen.
- No new gameplay-like UI metaphors that distract from learning.
- No reduced accessibility for style.
