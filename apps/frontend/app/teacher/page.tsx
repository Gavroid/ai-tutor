"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Header from "@/components/Header";
import type { MaterialListItem, MaterialStatus, User } from "@/types";

const STATUS_LABEL: Record<MaterialStatus, string> = {
  draft: "Черновик",
  ai_generated: "AI сгенерировал",
  teacher_approved: "Одобрено",
  published: "Опубликовано",
};

const STATUS_COLOR: Record<MaterialStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  ai_generated: "bg-amber-100 text-amber-800",
  teacher_approved: "bg-sky-100 text-sky-800",
  published: "bg-emerald-100 text-emerald-800",
};

export default function TeacherPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<MaterialListItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<MaterialStatus | "">("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Sprint 27: cookie-based auth. Если /me вернёт 401 → редирект.
    api.me().then(setUser).catch(() => {
      router.push("/login");
    });
  }, [router]);

  useEffect(() => {
    if (!user) return;
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, statusFilter]);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.teacherListMaterials({
        status: statusFilter || undefined,
      });
      setItems(data);
    } catch (e: any) {
      setError(e?.body?.detail || "Ошибка загрузки (нужны права учителя)");
    } finally {
      setBusy(false);
    }
  }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const visiblePublished = items.filter((item) => item.status === "published").length;
  const ownDrafts = items.filter((item) => item.generated_by === user?.id && item.status !== "published").length;

  return (
    <main className="prism-shell teacher-console min-h-dvh">
      <Header user={user} backHref="/subjects" title="Учительская" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer p-5 lg:p-10">
      <section className="border-b border-[color:var(--prism-line)] pb-5">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← На главную
        </Link>
        <div className="mt-1 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Учительская</h1>
          <div className="flex gap-2">
            <Link
              href="/teacher/topics"
              className="prism-action"
            >
              Готовность тем
            </Link>
            <Link
              href="/teacher/generate"
              className="prism-action primary"
            >
              + Сгенерировать материал
            </Link>
          </div>
        </div>
        {user && (
          <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
            <p className="prism-copy max-w-3xl">
              {user.role === "admin"
                ? `Админ-режим: ${user.display_name} видит всю библиотеку и может модерировать материалы.`
                : `Здравствуйте, ${user.display_name}. Здесь видна опубликованная библиотека и ваши черновики.`}
            </p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <MiniMetric label="Материалов" value={items.length} />
              <MiniMetric label="Опубликовано" value={visiblePublished} />
              <MiniMetric label="Моих черновиков" value={ownDrafts} />
            </div>
          </div>
        )}
      </section>

      <div className="mt-5 flex flex-wrap gap-2">
        <FilterChip active={statusFilter === ""} onClick={() => setStatusFilter("")}>
          Все
        </FilterChip>
        {(Object.keys(STATUS_LABEL) as MaterialStatus[]).map((s) => (
          <FilterChip
            key={s}
            active={statusFilter === s}
            onClick={() => setStatusFilter(s)}
          >
            {STATUS_LABEL[s]}
          </FilterChip>
        ))}
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="mt-5">
        {busy && <div className="text-sm text-slate-500">Загрузка…</div>}

        {!busy && items.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <p className="text-slate-500">
              Пока нет материалов.{" "}
              <Link
                href="/teacher/generate"
                className="text-sky-600 hover:underline"
              >
                Сгенерировать первый →
              </Link>
            </p>
          </div>
        )}

        {!busy && items.length > 0 && (
          <div className="grid gap-3">
            {items.map((m) => (
              <Link
                key={m.id}
                href={`/teacher/materials/${m.id}`}
                className="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-sky-300 hover:shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-base font-semibold text-slate-900">
                      #{m.id} · {m.title}
                    </h3>
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                      <span>Тема #{m.topic_id}</span>
                      <span>·</span>
                      <span>{fmtDate(m.created_at)}</span>
                      {m.published_at && (
                        <>
                          <span>·</span>
                          <span>Опубликовано: {fmtDate(m.published_at)}</span>
                        </>
                      )}
                    </div>
                  </div>
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${STATUS_COLOR[m.status]}`}
                  >
                    {STATUS_LABEL[m.status]}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
        </div>
        </div>
      </section>
    </main>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button onClick={onClick} className={`prism-pill ${active ? "active" : ""}`}>
      {children}
    </button>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-3xl border border-[color:var(--prism-line)] bg-black/10 p-3">
      <div className="text-[10px] font-black uppercase tracking-[0.16em] text-[color:var(--prism-muted)]">{label}</div>
      <div className="mt-1 text-xl font-black text-[color:var(--prism-ink)]">{value}</div>
    </div>
  );
}
