"use client";

/**
 * StatusChip — единый бейдж статуса готовности предмета.
 *
 * Sprint 2026-08-23 (H2.4): раньше все subjects показывали "MVP-ready"
 * независимо от реального mvp_status / blocked_reason. Это вводило
 * ребёнка в заблуждение. Теперь badge зависит от evidence-derived
 * mvp_status:
 *
 *   mvp_ready    → зелёный ✅ MVP-ready
 *   internal_mvp → амбер  ⏳ В обработке
 *   blocked_ocr  → красный 📚 OCR-заблокировано
 *   not_available→ красный 🚫 Недоступно
 *   preview      → нейтральный 🔍 Preview
 *
 * Per-role: student видит pilot-visible только. Этот компонент
 * отображает badge для УЖЕ отфильтрованного списка.
 */
import React from "react";

export type SubjectStatus =
  | "mvp_ready"
  | "internal_mvp"
  | "blocked_ocr"
  | "not_available"
  | "preview"
  | undefined;

export interface StatusChipProps {
  status: SubjectStatus;
  blockedReason?: string | null;
  pilotVisible?: boolean;
  size?: "sm" | "md";
}

const STATUS_COPY: Record<
  string,
  { label: string; icon: string; tone: "green" | "amber" | "red" | "neutral" }
> = {
  mvp_ready: { label: "MVP-ready", icon: "✅", tone: "green" },
  internal_mvp: { label: "В обработке", icon: "⏳", tone: "amber" },
  blocked_ocr: { label: "OCR-заблокировано", icon: "📚", tone: "red" },
  not_available: { label: "Недоступно", icon: "🚫", tone: "red" },
  preview: { label: "Preview", icon: "🔍", tone: "neutral" },
};

export function statusLabelFor(
  status: string | undefined,
  blockedReason?: string | null,
): { label: string; icon: string; tone: string } {
  if (!status) {
    return { label: "Preview", icon: "🔍", tone: "neutral" };
  }
  // Если есть явный blocked_reason и mvp_status не mvp_ready — показываем деталь.
  if (blockedReason === "blocked_ocr" && status !== "mvp_ready") {
    return { label: "OCR-заблокировано", icon: "📚", tone: "red" };
  }
  return (
    STATUS_COPY[status] ?? { label: status, icon: "🔍", tone: "neutral" }
  );
}

export function StatusChip({
  status,
  blockedReason,
  pilotVisible = true,
  size = "sm",
}: StatusChipProps) {
  const copy = statusLabelFor(status, blockedReason);
  const toneClass =
    copy.tone === "green"
      ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200"
      : copy.tone === "amber"
        ? "border-amber-400/40 bg-amber-500/10 text-amber-200"
        : copy.tone === "red"
          ? "border-rose-400/40 bg-rose-500/10 text-rose-200"
          : "border-white/15 bg-white/5 text-white/70";
  const paddingClass = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-black uppercase tracking-[0.14em] ${toneClass} ${paddingClass}`}
      data-status={status ?? "unknown"}
      data-pilot-visible={pilotVisible ? "true" : "false"}
    >
      <span aria-hidden="true">{copy.icon}</span>
      <span>{copy.label}</span>
    </span>
  );
}