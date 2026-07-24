"use client";

/**
 * Sprint 16.2 P2-5: Global error boundary для root layout failures.
 *
 * Если упал сам root layout (например, сломан провайдер), Next.js рендерит
 * этот fallback. Минимальный HTML — без зависимостей от layout.
 *
 * T1D-friendly: спокойное сообщение, нет давления.
 */

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ru">
      <body>
        <main
          style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "1.5rem",
            textAlign: "center",
            fontFamily: "system-ui, -apple-system, sans-serif",
          }}
          role="alert"
          aria-live="assertive"
        >
          <div style={{ maxWidth: "28rem" }}>
            <div style={{ fontSize: "3.5rem", marginBottom: "1rem" }}>🌿</div>

            <h1 style={{ fontSize: "1.5rem", marginBottom: "0.75rem" }}>
              Что-то пошло не так
            </h1>

            <p style={{ marginBottom: "0.5rem", color: "#475569" }}>
              Не переживай — твои ответы сохранены.
            </p>

            <p
              style={{
                marginBottom: "1.5rem",
                color: "#64748b",
                fontSize: "0.875rem",
              }}
            >
              Можешь попробовать ещё раз или вернуться на главную.
            </p>

            <button
              onClick={reset}
              style={{
                minHeight: "48px",
                padding: "0.75rem 1.5rem",
                background: "#0284c7",
                color: "white",
                border: "none",
                borderRadius: "0.5rem",
                fontSize: "1rem",
                fontWeight: "500",
                cursor: "pointer",
              }}
            >
              Попробовать снова
            </button>

            {error.digest && (
              <p
                style={{
                  marginTop: "1.5rem",
                  fontSize: "0.75rem",
                  color: "#94a3b8",
                  fontFamily: "monospace",
                }}
              >
                Код ошибки: {error.digest}
              </p>
            )}
          </div>
        </main>
      </body>
    </html>
  );
}