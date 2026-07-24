"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, getToken, setToken } from "@/lib/api";
import type { MaterialListItem, User } from "@/types";

export default function TeacherMaterialsListPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [materials, setMaterials] = useState<MaterialListItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Sprint 27: cookie-based auth. /me 401 → /login.
    api.me().then(setUser).catch(() => {
      router.push("/login");
    });
  }, [router]);

  useEffect(() => {
    if (!user) return;
    refresh();
  }, [user]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const list = await api.teacherListMaterials({ limit: 100 });
      setMaterials(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!user) {
    return <div className="p-6 text-slate-500">Загрузка...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">📚 Учебные материалы</h1>
        <Link
          href="/teacher"
          className="rounded-md bg-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-300"
        >
          ← Назад
        </Link>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">
          Ошибка: {error}
        </div>
      )}

      {busy && materials.length === 0 ? (
        <div className="text-slate-500">Загрузка материалов...</div>
      ) : materials.length === 0 ? (
        <div className="rounded-md bg-slate-50 px-4 py-8 text-center text-slate-500">
          Пока нет материалов. Используйте /teacher/generate для AI-генерации или
          загрузите PDF через /teacher/materials/upload.
        </div>
      ) : (
        <div className="space-y-2">
          {materials.map((m) => (
            <Link
              key={m.id}
              href={`/teacher/materials/${m.id}`}
              className="block rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:border-sky-300 hover:shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900">{m.title}</h3>
                  <p className="mt-1 text-sm text-slate-600">
                    Тема #{m.topic_id} · {m.status} · {new Date(m.created_at).toLocaleString("ru-RU")}
                  </p>
                </div>
                <div className="text-xs text-slate-400">#{m.id}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}