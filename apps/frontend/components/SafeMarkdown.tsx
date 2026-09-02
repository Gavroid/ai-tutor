"use client";

// Sprint 3.9.7 — рендер AI-ответов.
// - Streaming cursor: мягкая pulsing dot 6px (вместо ▍).
// - Copy handler: вешает onclick на все [data-md-copy] элементы
//   после монтирования / обновления HTML.

import { useEffect, useRef } from "react";
import { renderMarkdown } from "@/lib/markdown";

interface SafeMarkdownProps {
  text: string;
  /** Если true — рендерит в typewriter-стиле с pulsing dot cursor. */
  streaming?: boolean;
  className?: string;
}

export default function SafeMarkdown({
  text,
  streaming = false,
  className = "",
}: SafeMarkdownProps) {
  const ref = useRef<HTMLDivElement>(null);
  const html = renderMarkdown(text || "");
  const cursor = streaming ? '<span class="md-cursor" aria-hidden="true"></span>' : "";

  // Sprint 3.9.7: вешаем handler копирования для всех кнопок с data-md-copy.
  useEffect(() => {
    if (!ref.current) return;
    const buttons = ref.current.querySelectorAll<HTMLButtonElement>("[data-md-copy]");
    const onClick = async (ev: Event) => {
      const btn = ev.currentTarget as HTMLButtonElement;
      const value = btn.getAttribute("data-md-copy") ?? "";
      try {
        await navigator.clipboard.writeText(value);
        const original = btn.innerHTML;
        btn.classList.add("md-codeblock-copy-ok");
        btn.innerHTML = btn.innerHTML.replace("Скопировать", "Скопировано ✓");
        setTimeout(() => {
          btn.classList.remove("md-codeblock-copy-ok");
          btn.innerHTML = original;
        }, 1500);
      } catch {
        // Fallback — execCommand.
        const ta = document.createElement("textarea");
        ta.value = value;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
        } catch {
          /* ignore */
        }
        document.body.removeChild(ta);
      }
    };
    buttons.forEach((b) => b.addEventListener("click", onClick));
    return () => {
      buttons.forEach((b) => b.removeEventListener("click", onClick));
    };
  }, [html]);

  return (
    <div
      ref={ref}
      className={`md-stream ${className}`}
      dangerouslySetInnerHTML={{ __html: html + cursor }}
    />
  );
}
