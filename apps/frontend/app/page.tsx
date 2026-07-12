"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    router.push(getToken() ? "/subjects" : "/login");
  }, [router]);
  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-slate-500">Загрузка…</p>
    </main>
  );
}