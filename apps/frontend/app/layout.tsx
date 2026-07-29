import type { Metadata, Viewport } from "next";
import "./globals.css";
import ThemeToggle from "@/components/ThemeToggle";

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
    var saved = localStorage.getItem('ai-tutor:theme');
    var theme = saved || 'light';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    }
  } catch (e) {
    // localStorage может быть недоступен (приватный режим, sandbox).
    // MVP testing default: stay in readable light mode unless user explicitly toggles.
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <head>
        {/* Sprint 33: FOUC prevention — выполняется до hydration */}
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-app text-fg">
        {/* Sprint 11.2: a11y — skip-link для screen-reader / keyboard users.
           Tab → переход к основному контенту без tab через всю навигацию. */}
        <a href="#main-content" className="skip-link">
          Перейти к содержимому
        </a>
        <div id="main-content">{children}</div>
        {/* Sprint 5.3: переключатель темы в правом нижнем углу (фиксированный). */}
        <div className="fixed bottom-4 right-4 z-50">
          <ThemeToggle />
        </div>
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