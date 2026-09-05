/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone", // для минимального Docker-образа
  // Sprint 3.43 T1 follow-up: explicit config чтобы proxy.ts попал в manifest.
  // Next.js 16.2.10 Turbopack build имеет баг — proxy.ts компилируется в
  // .next/server/middleware.js, но middleware-manifest.json остаётся пустым
  // ("middleware": {}), и runtime НЕ вызывает proxy. Workaround: явный
  // experimental.proxy = true + project setting. После багфикса в Next.js 16.2.11+
  // можно убрать.
  experimental: {
    proxy: true,
  },
  async redirects() {
    return [
      { source: "/admin/users", destination: "/admin", permanent: false },
      { source: "/admin/tools", destination: "/admin", permanent: false },
      { source: "/admin/invites", destination: "/admin", permanent: false },
      { source: "/admin/realtime", destination: "/admin", permanent: false },
    ];
  },
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

export default nextConfig;