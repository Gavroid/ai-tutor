"use client";

interface SkeletonProps {
  className?: string;
  /** Sprint 11.4: визуальные размеры skeleton. */
  width?: string;
  height?: string;
}

/**
 * Sprint 11.4 — Loading skeleton (анимированный placeholder).
 * Используется вместо "Загрузка..." текста чтобы не было
 * скачков layout при loading.
 */
export default function Skeleton({
  className = "",
  width = "w-full",
  height = "h-4",
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`${width} ${height} animate-pulse rounded bg-slate-200 dark:bg-slate-700 ${className}`}
    />
  );
}
