/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone", // для минимального Docker-образа
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