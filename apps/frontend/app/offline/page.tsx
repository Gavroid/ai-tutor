"use client";

// Sprint 98: offline page для service worker fallback.


export default function OfflinePage() {
  return (
    <div
      data-testid="offline-page"
      className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-8 dark:bg-slate-900"
    >
      <div className="max-w-md text-center">
        <div className="mb-6 text-6xl">📡</div>
        <h1 className="mb-4 text-2xl font-bold text-[color:var(--prism-ink)] dark:text-slate-100">
          Нет соединения
        </h1>
        <p className="mb-6 text-slate-600 dark:text-slate-400">
          Похоже, ты офлайн. Проверь подключение к интернету и попробуй ещё раз.
        </p>
        <p className="text-sm text-slate-500 dark:text-slate-500">
          Некоторые темы могут быть доступны в кеше.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-6 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Попробовать снова
        </button>
      </div>
    </div>
  );
}