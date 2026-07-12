"use client";

/**
 * WebSocket-клиент для AI-чата с авто-reconnect.
 * Подключается к /ws/ai/chat?token=<jwt>, стримит chunks ответа AI.
 * Поддерживает:
 *   - exponential backoff reconnect при разрыве
 *   - timeout для подвисших соединений
 *   - heartbeat ping для keepalive
 *   - ручное закрытие через cancel()
 */

import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export type ChatMsg = {
  role: "user" | "assistant";
  content: string;
};

export type WSStatus =
  | "idle"
  | "connecting"
  | "open"
  | "closed"
  | "reconnecting"
  | "error";

type StreamCallbacks = {
  onChunk: (chunk: string) => void;
  onDone: (meta: {
    model?: string;
    input_tokens?: number;
    output_tokens?: number;
  }) => void;
  onError: (message: string) => void;
};

type WSConfig = {
  /** Initial reconnect delay (ms). Default 500 */
  initialDelay?: number;
  /** Max reconnect delay (ms). Default 30000 (30s) */
  maxDelay?: number;
  /** Maximum reconnect attempts. Default 10 */
  maxAttempts?: number;
  /** Heartbeat interval (ms). Default 25000 */
  heartbeatInterval?: number;
  /** Connection timeout (ms). Default 15000 */
  connectionTimeout?: number;
};

const DEFAULT_CONFIG: Required<WSConfig> = {
  initialDelay: 500,
  maxDelay: 30000,
  maxAttempts: 10,
  heartbeatInterval: 25000,
  connectionTimeout: 15000,
};

/** Открыть WS с auto-reconnect. Возвращает cancel function. */
export function streamChat(
  token: string,
  history: ChatMsg[],
  topicId: number | undefined,
  cb: StreamCallbacks,
  config: WSConfig = {}
): () => void {
  const cfg = { ...DEFAULT_CONFIG, ...config };

  // ws://host/ws/ai/chat?token=... — заменяем https/http на ws/wss
  const wsBase = API_URL.replace(/^https/, "wss").replace(/^http/, "ws");
  const url = `${wsBase}/ws/ai/chat?token=${encodeURIComponent(token)}`;

  let ws: WebSocket | null = null;
  let attempt = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let connectionTimer: ReturnType<typeof setTimeout> | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  let manuallyClosed = false;
  let payload: { history: ChatMsg[]; topicId: number | undefined } | null = null;

  function cleanup() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (connectionTimer) {
      clearTimeout(connectionTimer);
      connectionTimer = null;
    }
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
    if (ws) {
      try {
        ws.close();
      } catch {}
      ws = null;
    }
  }

  function connect() {
    cleanup();

    if (manuallyClosed) return;
    if (attempt >= cfg.maxAttempts) {
      cb.onError(`WS: превышен лимит реконнектов (${cfg.maxAttempts})`);
      return;
    }

    attempt++;
    const ws = new WebSocket(url);
    let opened = false;

    // Timeout: если WS не открылся за connectionTimeout — закрываем и реконнект
    connectionTimer = setTimeout(() => {
      if (!opened) {
        try {
          ws.close();
        } catch {}
      }
    }, cfg.connectionTimeout);

    ws.onopen = () => {
      opened = true;
      attempt = 0; // сброс после успешного connect
      if (connectionTimer) {
        clearTimeout(connectionTimer);
        connectionTimer = null;
      }

      // Отправляем payload если есть (для reconnect — повторно посылаем)
      if (payload) {
        try {
          ws.send(JSON.stringify(payload));
        } catch {
          // ignore
        }
      }

      // Heartbeat: шлём ping каждые 25s чтобы соединение не зависло
      heartbeatTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(JSON.stringify({ type: "ping" }));
          } catch {}
        }
      }, cfg.heartbeatInterval);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "chunk") cb.onChunk(msg.content || "");
        else if (msg.type === "done") {
          cb.onDone({
            model: msg.model,
            input_tokens: msg.input_tokens,
            output_tokens: msg.output_tokens,
          });
          // Успешный done — закрываем нормально
          manuallyClosed = true;
          cleanup();
          return;
        } else if (msg.type === "pong") {
          // heartbeat response — ignore
        } else if (msg.type === "error") {
          cb.onError(msg.message || "WS error");
        }
      } catch {
        cb.onError("Невалидный ответ сервера");
      }
    };

    ws.onerror = () => {
      // onerror всегда сопровождается onclose — reconnect там
    };

    ws.onclose = (ev) => {
      cleanup();

      if (manuallyClosed) {
        if (ev.code !== 1000) cb.onError(`WS закрыт (code=${ev.code})`);
        return;
      }

      // Нормальный close после done — не реконнект
      if (ev.code === 1000) return;

      // Exponential backoff: 500, 1000, 2000, 4000, 8000, ... max 30s
      const delay = Math.min(
        cfg.initialDelay * Math.pow(2, attempt - 1),
        cfg.maxDelay
      );

      cb.onError(`WS закрыт (code=${ev.code}), реконнект через ${delay}ms`);

      reconnectTimer = setTimeout(() => {
        connect();
      }, delay);
    };
  }

  // Изначальный payload
  payload = { history, topicId };

  // Старт
  connect();

  return () => {
    manuallyClosed = true;
    cleanup();
  };
}

/** React hook: статус WS-соединения + helpers для стриминга. */
export function useChatStream(token: string | null) {
  const [status, setStatus] = useState<WSStatus>("idle");
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      // При размонтировании закрываем WS
      if (cancelRef.current) cancelRef.current();
    };
  }, []);

  const send = useCallback(
    (
      history: ChatMsg[],
      topicId: number | undefined,
      cb: StreamCallbacks
    ) => {
      if (!token) {
        cb.onError("Не авторизован");
        return;
      }
      // Отменяем предыдущий
      if (cancelRef.current) cancelRef.current();
      setStatus("connecting");
      cancelRef.current = streamChat(token, history, topicId, {
        ...cb,
        onError: (m) => {
          setStatus("error");
          cb.onError(m);
        },
      });
      // onopen будет вызван после connect → setStatus("open") можно делать там,
      // но для простоты сразу "open" (если бы был closed — была бы ошибка)
      setStatus("open");
    },
    [token]
  );

  return {
    status,
    cancel: () => {
      if (cancelRef.current) {
        cancelRef.current();
        cancelRef.current = null;
        setStatus("closed");
      }
    },
    send,
  };
}
