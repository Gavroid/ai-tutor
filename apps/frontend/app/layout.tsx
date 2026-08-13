import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./styles/prism-foundation.css";
import "./styles/prism-v3.css";
import "./styles/split-lesson.css";
import "./styles/console-surfaces.css";
import "./styles/mobile-chat.css";

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
  try {
    if (location.hostname === 'school431a.ru') {
      location.replace('https://school.431a.ru' + location.pathname + location.search + location.hash);
      return;
    }
    document.documentElement.classList.add('dark');
    document.documentElement.dataset.theme = 'dark';
    localStorage.setItem('ai-tutor:theme', 'dark');
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
        <div id="main-content">{children}</div>
        {/* Sprint 98: register service worker для PWA offline support. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  navigator.serviceWorker.register('/sw.js').then(
                    (reg) => console.log('[SW] Registered scope:', reg.scope),
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