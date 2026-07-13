"use client";

/**
 * Real-time WS клиент для /api/v1/admin/ws (Sprint 9.3).
 * Подключается к WS endpoint, стримит JSON-снапшоты каждые ~2 секунды.
 */

export type AdminSnapshot = {
  ts: string;
  ai_modes: Record<string, { ok: number; error: number }>;
  ai_tokens: Record<string, number>;
  http_total: { "2xx": number; "4xx": number; "5xx": number };
  system: {
    db: string;
    redis: string;
    backend: string;
    mem_used_pct: number | null;
  };
};

export type AdminWSState =
  | { status: "connecting" }
  | { status: "open"; last: AdminSnapshot }
  | { status: "closed"; reason?: string }
  | { status: "error"; error: string };

export type AdminWSListener = (state: AdminWSState) => void;

export class AdminWSConnection {
  private ws: WebSocket | null = null;
  private retries = 0;
  private closed = false;

  constructor(
    private readonly getToken: () => string | null,
    private readonly listener: AdminWSListener,
  ) {}

  start(): void {
    if (this.closed) return;
    const token = this.getToken();
    if (!token) {
      this.listener({ status: "error", error: "No auth token" });
      return;
    }
    this.listener({ status: "connecting" });

    // Build WS URL from current page origin (so HTTPS uses wss://, HTTP uses ws://)
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${window.location.host}/api/v1/admin/ws?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      this.listener({ status: "error", error: String(e) });
      return;
    }

    this.ws.onopen = () => {
      this.retries = 0;
    };

    this.ws.onmessage = (ev) => {
      try {
        const snap: AdminSnapshot = JSON.parse(ev.data);
        this.listener({ status: "open", last: snap });
      } catch (e) {
        // ignore malformed message
      }
    };

    this.ws.onerror = () => {
      this.listener({ status: "error", error: "WebSocket error" });
    };

    this.ws.onclose = (ev) => {
      this.listener({ status: "closed", reason: ev.reason });
      if (!this.closed) {
        this.retries = Math.min(this.retries + 1, 6);
        const delay = Math.min(1000 * Math.pow(2, this.retries), 30_000);
        window.setTimeout(() => this.start(), delay);
      }
    };
  }

  close(): void {
    this.closed = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
