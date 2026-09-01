/**
 * Sprint 3.7 / Polish: client-side crash reporter.
 *
 * Лёгкий ring-buffer в localStorage. Ловит:
 *   - window.onerror (uncaught exceptions)
 *   - unhandledrejection (promise rejections)
 *   - ручные report() вызовы (например, из error.tsx)
 *
 * Хранит последние 50 событий. Не отправляет на бэкенд автоматически —
 * родитель/Кирилл может нажать "Скопировать" в error.tsx и прислать JSON
 * в поддержку.
 *
 * Публичный API:
 *   - initCrashReporter()       — вызывается ОДИН раз из client-layout
 *   - report(error, context?)   — ручной report
 *   - getRecentCrashes(limit?)  — для UI "последние ошибки"
 *   - clearCrashes()            — очистить буфер
 *   - formatCrashesForCopy()    — pretty JSON для копирования в поддержку
 */

"use client";

const STORAGE_KEY = "ai-tutor:crash-log:v1";
const MAX_EVENTS = 50;

export interface CrashEvent {
  /** Уникальный id для поддержки (8 символов hex). */
  id: string;
  /** ISO-8601 timestamp. */
  ts: string;
  /** Тип ошибки. */
  kind: "uncaught" | "unhandledrejection" | "manual" | "boundary";
  /** Сообщение ошибки (или сериализованный reason для rejection). */
  message: string;
  /** Stack trace, если доступен. */
  stack?: string;
  /** Доп. контекст (component, action). */
  context?: Record<string, unknown>;
  /** URL где произошло. */
  url: string;
  /** User-Agent (короткий). */
  ua: string;
}

function shortId(): string {
  // 8 hex chars: достаточно для нашего объёма, не крипто.
  return Math.floor(Math.random() * 0xffffffff)
    .toString(16)
    .padStart(8, "0");
}

function safeStorage(): Storage | null {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage;
  } catch {
    return null;
  }
}

function readBuffer(): CrashEvent[] {
  const s = safeStorage();
  if (!s) return [];
  try {
    const raw = s.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeBuffer(events: CrashEvent[]): void {
  const s = safeStorage();
  if (!s) return;
  try {
    s.setItem(STORAGE_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
  } catch {
    // QuotaExceeded — не критично, просто теряем старые события.
  }
}

function pushEvent(ev: CrashEvent): void {
  const buf = readBuffer();
  buf.push(ev);
  writeBuffer(buf);
}

function shortUA(): string {
  if (typeof navigator === "undefined") return "server";
  // Берём первую "значимую" часть UA (не весь ~200-символьный chrome blob).
  const ua = navigator.userAgent || "";
  return ua.slice(0, 120);
}

function serializeReason(reason: unknown): { message: string; stack?: string } {
  if (reason instanceof Error) {
    return { message: reason.message, stack: reason.stack };
  }
  if (typeof reason === "string") {
    return { message: reason };
  }
  try {
    return { message: `Non-Error rejection: ${JSON.stringify(reason)}` };
  } catch {
    return { message: "Non-Error rejection (unserializable)" };
  }
}

let initialized = false;

/**
 * Инициализирует глобальные listeners. Вызывайте один раз на client-mount.
 * Safe to call multiple times — guard на `initialized`.
 */
export function initCrashReporter(): void {
  if (initialized || typeof window === "undefined") return;
  initialized = true;

  // window.onerror: (msg, src, lineno, colno, error) => true
  window.addEventListener("error", (e) => {
    const err = e.error;
    report(err ?? e.message, {
      kind: "uncaught",
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
    });
  });

  // unhandledrejection: (event) => event.reason
  window.addEventListener("unhandledrejection", (e) => {
    const { message, stack } = serializeReason(e.reason);
    report({ message, stack }, { kind: "unhandledrejection" });
  });
}

/**
 * Ручной report. Используется из error.tsx (React Error Boundary).
 */
export function report(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  if (typeof window === "undefined") return;
  let message = "Unknown error";
  let stack: string | undefined;
  if (error instanceof Error) {
    message = error.message || error.name || "Error";
    stack = error.stack;
  } else if (typeof error === "string") {
    message = error;
  } else if (error && typeof error === "object") {
    try {
      message = JSON.stringify(error);
    } catch {
      message = "Unserializable error object";
    }
  }

  pushEvent({
    id: shortId(),
    ts: new Date().toISOString(),
    kind: (context?.kind as CrashEvent["kind"]) ?? "manual",
    message: message.slice(0, 2000),
    stack: stack?.slice(0, 4000),
    context,
    url: window.location?.pathname ?? "?",
    ua: shortUA(),
  });
}

export function getRecentCrashes(limit = 20): CrashEvent[] {
  const buf = readBuffer();
  return buf.slice(-limit).reverse(); // новейшие сверху
}

export function clearCrashes(): void {
  const s = safeStorage();
  if (!s) return;
  s.removeItem(STORAGE_KEY);
}

/**
 * Pretty-формат для копирования в поддержку / письмо.
 */
export function formatCrashesForCopy(events?: CrashEvent[]): string {
  const list = events ?? getRecentCrashes();
  if (list.length === 0) return "(no crashes recorded)";
  return JSON.stringify(
    {
      exported_at: new Date().toISOString(),
      count: list.length,
      crashes: list,
    },
    null,
    2,
  );
}
