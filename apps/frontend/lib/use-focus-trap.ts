"use client";

import { useEffect, useRef } from "react";

/**
 * Sprint 14 — focus-trap для модалок.
 *
 * Что делает:
 * 1. На открытии — ставит focus на первый focusable элемент модалки.
 * 2. Tab / Shift+Tab внутри модалки — зацикливает внутри (focus-trap).
 * 3. Escape — закрывает через onEscape.
 * 4. Возвращает фокус обратно на element открыватель при unmount.
 * 5. aria-modal=true + role=dialog (wc 2.4.3 focus order).
 *
 * Использование:
 *   const trapRef = useFocusTrap({ active: isOpen, onEscape: () => setOpen(false) });
 *   <div ref={trapRef} role="dialog" aria-modal="true" tabIndex={-1}>...</div>
 */
export function useFocusTrap({
  active,
  onEscape,
}: {
  active: boolean;
  onEscape: () => void;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!active) return;
    // Sprint 14: сохраняем element открыватель чтобы вернуть focus после close.
    lastFocusedRef.current = document.activeElement as HTMLElement | null;

    const root = ref.current;
    if (!root) return;

    // На открытии — focus первый interactive element или сам root.
    const focusables = getFocusables(root);
    if (focusables.length > 0) {
      focusables[0].focus();
    } else {
      root.tabIndex = -1;
      root.focus();
    }

    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onEscape();
        return;
      }
      if (e.key !== "Tab" || !root) return;
      const items = getFocusables(root);
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey) {
        if (active === first || !root.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKey);

    return () => {
      document.removeEventListener("keydown", handleKey);
      // Возвращаем focus на element открыватель.
      const prev = lastFocusedRef.current;
      if (prev && document.body.contains(prev)) {
        prev.focus();
      }
    };
  }, [active, onEscape]);

  return ref;
}

function getFocusables(root: HTMLDivElement): HTMLElement[] {
  const sel =
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  return Array.from(root.querySelectorAll<HTMLElement>(sel));
}
