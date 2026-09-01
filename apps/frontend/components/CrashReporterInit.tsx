"use client";

/**
 * Sprint 3.7 / Polish: client-mount init для crash-reporter.
 * Импортируется в layout.tsx, чтобы listeners установились при загрузке.
 * Self-contained — никаких side-effects кроме подписки на window events.
 */

import { useEffect } from "react";
import { initCrashReporter } from "@/lib/crash-reporter";

export default function CrashReporterInit() {
  useEffect(() => {
    initCrashReporter();
  }, []);
  return null;
}
