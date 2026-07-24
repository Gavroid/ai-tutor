"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    // Sprint 27: проверяем cookie через /me (async). Если 401 → /login.
    api.isAuthenticated().then((ok) => {
      router.push(ok ? "/subjects" : "/login");
    });
  }, [router]);
  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-slate-500">Загрузка…</p>
    </main>
  );
}