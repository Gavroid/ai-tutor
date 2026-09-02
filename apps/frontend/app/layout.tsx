import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./styles/prism-foundation.css";
import "./styles/prism-v3.css";
import "./styles/split-lesson.css";
import "./styles/console-surfaces.css";
import "./styles/mobile-chat.css";
import CrashReporterInit from "@/components/CrashReporterInit";

export const metadata: Metadata = {
  title: "AI-репетитор 7 класса",
  description: "Персональный AI-репетитор для школьной программы 7 класса",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Репетитор",
  },
};

export const viewport: Viewport = {
  themeColor: "#0284c7",
  width: "device-width",
  initialScale: 1,
};

/**
 * Sprint 33: inline script для предотвращения FOUC (Flash of Unstyled Content).
 *
 * Без этого скрипта, на 1-2 фрейма до React hydration пользователь видит
 * светлую тему (если у него тёмная в localStorage). Это раздражает и
 * выглядит непрофессионально.
 *
 * Скрипт выполняется ДО рендера body — устанавливает class="dark" на <html>
 * сразу при парсинге HTML.
 */
const themeInitScript = `
(function() {
  // Sprint 3.9.2: только тёмная тема. ThemeToggle убран,
  // light/system выбор больше недоступен. Всегда принудительно dark.
  try {
    if (location.hostname === 'school431a.ru') {
      location.replace('https://school.431a.ru' + location.pathname + location.search + location.hash);
      return;
    }
    document.documentElement.classList.add('dark');
    document.documentElement.dataset.theme = 'dark';
  } catch (e) {
    document.documentElement.classList.add('dark');
    document.documentElement.dataset.theme = 'dark';
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <head>
        <meta name="color-scheme" content="dark" />
        {/* Sprint 33: FOUC prevention — выполняется до hydration */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-app text-fg">
        {/* Sprint H2.5 / U2.1: skip-link для keyboard users. */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-bold focus:text-slate-900"
        >
          Пропустить навигацию
        </a>
        <div id="main-content" tabIndex={-1}>
          {children}
        </div>
        {/* Sprint 3.7: client-side crash reporter init (no-op рендер). */}
        <CrashReporterInit />
        {/* Sprint 3.7 polish: theme switcher — теперь встроен в Header,
            не поверх fixed (раньше перекрывал «Фидбек/Выйти» в правом
            верхнем углу в light mode). */}
        {/* Sprint 98: register service worker для PWA offline support. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  // S0.5 (2026-08-31): no console.log in production code.
                  // Success is silent; only surface registration failures so
                  // an offline-capable regression can't pass unnoticed.
                  navigator.serviceWorker.register('/sw.js').catch(
                    (err) => console.warn('[SW] Registration failed:', err)
                  );
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}