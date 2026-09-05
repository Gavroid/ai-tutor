/**
 * Sprint 3.43 T1: Next.js PROXY (бывший middleware) для Content-Security-Policy (CSP).
 *
 * NOTE: Next.js 16 переименовал middleware → proxy (документация:
 * https://nextjs.org/docs/app/api-reference/file-conventions/proxy).
 * Этот файл — proxy.ts с функцией `proxy()`, не middleware.ts.
 *
 * ЗАЧЕМ: Sprint 3.38 ставил CSP header в FastAPI middleware, но HTML
 * отдаётся Next.js через reverse proxy. Браузер **не видел** CSP header,
 * потому что FastAPI обслуживает только API endpoints, а не HTML страницы.
 * Аудит 2026-09-05 нашёл эту проблему (P1).
 *
 * РЕШЕНИЕ (T1 из аудита, вариант A-модифицированный): CSP генерируется
 * в Next.js proxy, который добавляет header в каждый HTML response.
 * Per-request nonce для script-src (Strict-Dynamic baseline), чтобы
 * убрать 'unsafe-inline' (Sprint 3.38 compromise).
 *
 * NOTE: proxy.ts в Next.js App Router запускается на каждом request
 * (HTML pages и API routes под /api/*). Для /api/* нам всё ещё нужен
 * CSP из FastAPI (Sprint 3.38), но это будет другой CSP (для JSON,
 * строже — `default-src 'none'`).
 */

import { NextRequest, NextResponse } from "next/server";

/**
 * Генерирует криптографически стойкий nonce (base64, 16 байт).
 * Используется для script-src в CSP header.
 */
function generateNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  // base64 без padding для URL-safe nonce
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/**
 * Строит CSP policy с per-request nonce.
 * - script-src: 'self' + nonce + 'strict-dynamic' (позволяет nonce-loaded scripts грузить другие)
 * - style-src: 'self' + nonce + 'unsafe-inline' (Tailwind требует inline styles, см. Sprint 3.38)
 * - object-src: 'none' (анти-Flash/CSRF)
 * - base-uri: 'self' (анти-hijacking)
 * - frame-ancestors: 'none' (анти-clickjacking)
 * - report-uri: тот же что в Sprint 3.38 FastAPI CSP
 */
function buildCsp(nonce: string, reportUri: string): string {
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'nonce-${nonce}' 'unsafe-inline'`,
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https: ws: wss:",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    `report-uri ${reportUri}`,
  ];
  return directives.join("; ");
}

export function proxy(request: NextRequest) {
  // Sprint 3.43 T1: генерируем per-request nonce
  const nonce = generateNonce();

  // CSP report-uri для violation reports (тот же endpoint что в FastAPI Sprint 3.38).
  // Report-only mode (безопасный staged-rollout).
  const reportUri = `${request.nextUrl.origin}/api/v1/csp-report`;

  const csp = buildCsp(nonce, reportUri);

  // Sprint 3.43 T1: пробрасываем nonce в headers чтобы React/Next.js
  // мог использовать его для <Script nonce={...} /> (вне scope этой сессии,
  // но архитектурно готово).
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy-Report-Only", csp);

  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Sprint 3.43 T1: для HTML responses (text/html) добавляем CSP header.
  // Для API endpoints (application/json) CSP будет другим, FastAPI решает.
  response.headers.set("Content-Security-Policy-Report-Only", csp);
  response.headers.set("x-nonce", nonce);

  return response;
}

/**
 * Matcher исключает статические assets и API routes (API routes обслуживаются
 * FastAPI middleware, см. Sprint 3.38).
 *
 * Только HTML pages Next.js получают этот CSP. Это by-design:
 * - Static assets (CSS/JS chunks) не должны иметь CSP — они inline в HTML.
 * - /api/* идёт в FastAPI через reverse proxy, FastAPI middleware ставит свой CSP.
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * 1. /api/* (FastAPI handles — Sprint 3.38 CSP)
     * 2. /_next/static (static files)
     * 3. /_next/image (image optimization files)
     * 4. /favicon.ico, /sitemap.xml, /robots.txt (metadata files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
