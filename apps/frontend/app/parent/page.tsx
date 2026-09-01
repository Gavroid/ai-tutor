// Sprint S0.5 (2026-08-31): index-redirect for /parent → /parents.
//
// History: the parent area has /parents (list of linked children) and
// /parent/dashboard/[studentId] (per-child dashboard), but no /parent index.
// Direct hits to /parent returned 404, breaking links from emails / chat
// messages. This redirect matches the existing convention: parent signs in,
// then lands on the linked-children list at /parents, then drills into the
// per-child dashboard.
//
// Privacy: /parents is read-only for parents by design (D3.1, D3.2, D3.3 — no
// pause/limits, no chat visibility). The redirect preserves that boundary.

import { redirect } from "next/navigation";

export default function ParentIndexPage(): never {
  redirect("/parents");
}
