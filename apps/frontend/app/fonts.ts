// Sprint 3.9.7 — Шрифты через next/font/google.
// Подмножество cyrillic+latin, display: swap, без блокировки рендера.
//
// Семейства:
// - Inter Variable (body, ~17px, line-height 1.65)
// - Inter Display (h2/h3 заголовки ответов) — используется тот же Inter Variable,
//   но с font-feature-settings и более широким tracking.
// - JetBrains Mono (code, формулы)
//
// next/font сам скачивает, делает subset и self-hosts.

import { Inter, JetBrains_Mono } from "next/font/google";

// Body / UI / system.
export const inter = Inter({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-sans",
  weight: ["400", "500", "600", "700", "800"],
});

// Display variant — для заголовков h2/h3 в ответах AI. На уровне CSS используем
// тот же шрифт, но в markdown.css добавляем font-feature-settings и tracking.
export const interDisplay = Inter({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-display",
  weight: ["600", "700", "800", "900"],
});

// Code / формулы.
export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
  weight: ["400", "500", "700"],
});
