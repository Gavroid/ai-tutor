# AI-Tutor UI V3 Design Prompt

Date: 2026-08-02

## Task

Rewrite the AI-Tutor interface from scratch visually. Do not polish the old narrow SaaS layout. Build a new premium product interface inspired by the supplied sketches:

1. Futuristic AI / robotics landing page: dark glass frame, thin grid, blue accents, asymmetric hero, technical labels.
2. 3D nature diorama / dashboard: soft light mode, ivory cards, landscape-like layers, rounded product cards, tactile depth.
3. Museum / art-history interface: calm editorial sidebar, translucent panels, object focus, timeline metadata.
4. Dark startup accelerator mockup: wide dark SaaS canvas, purple highlights, bento metrics, wireframe objects.
5. Neon desk/studio mockup: layered screens, glow, saturated accents, high production value.

## Self-Critique Of Previous Attempts

Previous attempts failed because they recolored an existing narrow layout. They changed tokens but kept the old composition. The fix is compositional, not cosmetic.

## Design Strategy

Name: **Prism Learning OS**.

Surface archetypes:

- `/login`: Decide / Enter — dramatic portal into the product.
- `/subjects`: Explore — wide gallery/grid, not a narrow content feed.
- `/subjects/[id]`: Decide / Learn — subject object focus + route map.
- `/topics/[id]`: Operate / Learn — lesson cockpit with action rail, readable lesson stage, chat console.
- `/teacher/topics`: Monitor / Operate — readiness as mobile cards + desktop matrix.
- `/parent/dashboard/[studentId]`: Monitor — parent summary cockpit, not marketing hero.

## Visual Language

- Wide framed canvas, like a premium floating interface.
- Thin grid lines and glass panels, but contrast-safe.
- Dark theme: deep graphite/navy/purple, cyan/violet accents, technical labels.
- Light theme: ivory/sage/mist surfaces, soft diorama-like panels, dark ink text.
- Bento layouts with non-equal hierarchy.
- Strong oversized typography only where it helps orientation.
- Product surfaces over decoration; avoid random fake stats.
- No copyrighted GTA/robot/art assets; use abstract CSS shapes and UI geometry only.

## Modern Design Constraints From Web Research

- Bento grids are still useful because they encode hierarchy and collapse naturally on mobile.
- Dark mode must be first-class, not an inverted afterthought.
- Glassmorphism must be responsible: use it for layered depth, not low-contrast decoration.
- Mobile needs 44px+ tap targets, single-column stack, no horizontal tables.
- Performance matters: avoid heavy WebGL/large media; use CSS gradients and simple shapes.

## Build Rules

- Do not use the old Card/Button look as the composition baseline.
- Use new `prism-*` CSS utilities and raw layout for the main screens.
- Maintain existing business logic/API calls.
- Preserve accessibility: focus states, readable lesson content, mobile hit targets.
- Both light and dark themes must be explicitly designed.

## Slop Audit Target

Before shipping, score < 3/10:

- No old center-stack / narrow max-width feed.
- No equal feature cards with no hierarchy.
- No generic blue-purple gradient as the only idea.
- No glass surfaces without purpose.
- No unusable mobile horizontal overflow.
