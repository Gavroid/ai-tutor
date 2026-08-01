"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Subject, User } from "@/types";
import EmptyState from "@/components/EmptyState";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import Header from "@/components/Header";

type RecItem = {
  topic_id: number;
  topic_name: string;
  subject_id: number;
  subject_name: string;
  mastery_score: number;
  attempts_count: number;
  correct_count: number;
};

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [aiOk, setAiOk] = useState<boolean | null>(null);
  const [aiModel, setAiModel] = useState<string | null>(null);
  const [review, setReview] = useState<RecItem[]>([]);
  const [dueReview, setDueReview] = useState<
    Array<{
      topic_id: number;
      topic_name: string;
      subject_name: string;
      mastery_score: number;
      days_overdue: number;
    }>
  >([]);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((err: unknown) => {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          router.push("/login");
        } else {
          console.warn("api.me() failed (non-auth):", err);
        }
      });
    api.subjects().then(setSubjects).catch(() => {});
    api.aiPing().then((r) => { setAiOk(r.ok); setAiModel(r.model); }).catch(() => setAiOk(false));
    api.recommendReview().then(setReview).catch(() => {});
    api.dueForReview(10).then(setDueReview).catch(() => {});
  }, [router]);

  const q = searchQuery.trim().toLowerCase();
  const filtered = q
    ? subjects.filter((s) => s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q))
    : subjects;
  const readyCount = subjects.filter((s) => s.mvp_status === "mvp_ready").length;
  const previewCount = Math.max(subjects.length - readyCount, 0);

  return (
    <main className="premium-shell">
      <Header user={user} title={user ? `AI Tutor · ${user.display_name}` : "AI Tutor"} />
      <section className="premium-container px-1 py-5 sm:px-4 sm:py-10">
        <div className="premium-hero p-5 sm:p-9 lg:p-12">
          <div className="grid gap-8 lg:grid-cols-[1.25fr_0.75fr] lg:items-end">
            <div>
              <div className="premium-kicker">Neon Coast Learning · Pilot MVP</div>
              <h1 className="premium-title mt-5 max-w-4xl text-4xl font-black sm:text-6xl lg:text-7xl">
                Учёба, которая выглядит как продукт будущего.
              </h1>
              <p className="premium-copy mt-5 max-w-2xl text-lg sm:text-xl">
                Выбери предмет, начни тему и двигайся по маршруту: объяснение, практика, обратная связь, прогресс для взрослого.
              </p>
              <div className="premium-chip-row mt-7 flex flex-wrap gap-3 text-sm">
                <Link href="/diagnostic">Диагностика</Link>
                <Link href="/link-parent">Привязать родителя</Link>
                {user?.role === "parent" && <Link href="/parents">Родительский кабинет</Link>}
                {user?.role === "admin" && <Link href="/admin">Админ-панель</Link>}
                {(user?.role === "teacher" || user?.role === "admin") && <Link href="/teacher">Учительская</Link>}
              </div>
            </div>

            <aside className="premium-panel p-5 text-white">
              <div className="text-xs uppercase tracking-[0.24em] text-white/55">System Pulse</div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric label="Предметов" value={subjects.length || "—"} />
                <Metric label="MVP-ready" value={readyCount || "—"} />
                <Metric label="Preview" value={previewCount || "—"} />
                <Metric label="AI" value={aiOk === null ? "…" : aiOk ? "ON" : "OFF"} tone={aiOk ? "good" : "warn"} />
              </div>
              {aiOk === true && aiModel && <p className="mt-4 text-xs text-white/60">Модель: {aiModel}</p>}
            </aside>
          </div>
        </div>

        {(dueReview.length > 0 || review.length > 0) && (
          <section className="mt-7 grid gap-4 lg:grid-cols-2">
            {dueReview.length > 0 && (
              <ActionPanel title="Сегодня к повторению" tone="violet" items={dueReview.slice(0, 4).map((d) => ({ href: `/topics/${d.topic_id}`, title: d.topic_name, meta: `${d.subject_name} · ${d.days_overdue > 0 ? `просрочено ${d.days_overdue}д` : "сегодня"}` }))} />
            )}
            {review.length > 0 && (
              <ActionPanel title="Стоит повторить" tone="amber" items={review.slice(0, 4).map((r) => ({ href: `/topics/${r.topic_id}`, title: r.topic_name, meta: `${r.subject_name} · уверенность ${Math.round(r.mastery_score * 100)}%` }))} />
            )}
          </section>
        )}

        <section className="mt-8">
          <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="premium-kicker">Subject Grid</div>
              <h2 className="premium-title mt-3 text-3xl font-black sm:text-5xl">Выбери направление</h2>
              <p className="premium-copy mt-2 max-w-xl">Готовые темы помечены как MVP-ready. Остальные предметы открыты как preview, чтобы не обещать качество раньше времени.</p>
            </div>
            <div className="w-full lg:w-[420px]">
              <label htmlFor="subject-search" className="sr-only">Поиск предмета</label>
              <Input
                id="subject-search"
                type="search"
                inputMode="search"
                placeholder="Поиск: математика, русский, физика…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-12 rounded-2xl border-white/30 bg-white/95 px-5 shadow-glow"
              />
              <div className="mt-2 text-right text-xs text-white/55">
                {q ? `${filtered.length} из ${subjects.length} найдено` : `${subjects.length} предметов`}
              </div>
            </div>
          </div>

          {filtered.length > 0 ? (
            <div className="grid auto-rows-fr gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {filtered.map((s, idx) => (
                <Link key={s.id} href={`/subjects/${s.id}`} className="group block animate-slide-up" style={{ animationDelay: `${Math.min(idx * 35, 350)}ms` }}>
                  <article className={`premium-tile h-full p-5 transition-modern ${s.mvp_status === "mvp_ready" ? "premium-tile-featured md:col-span-2" : ""}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex size-14 items-center justify-center rounded-2xl brand-gradient text-3xl text-white shadow-glow">
                        {s.icon || "📘"}
                      </div>
                      <Badge variant={s.mvp_status === "mvp_ready" ? "success" : "warning"} size="sm">
                        {s.mvp_status === "mvp_ready" ? "MVP-ready" : "Preview"}
                      </Badge>
                    </div>
                    <h3 className="mt-5 text-2xl font-black tracking-tight text-[#171022] transition-modern group-hover:text-brand-600">
                      {s.name}
                    </h3>
                    {s.description && <p className="mt-2 line-clamp-3 text-sm text-[#4a3d5d]">{s.description}</p>}
                    <p className="mt-4 text-xs leading-relaxed text-[#6b5a80]">{s.support_note}</p>
                    <div className="mt-5 flex items-center justify-between border-t border-brand-200/60 pt-4 text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
                      <span>7 класс</span>
                      <span>Открыть →</span>
                    </div>
                  </article>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState icon="🔍" title={`Ничего не найдено по «${searchQuery}»`} description="Попробуй другой запрос, например: матем, русск, физика" variant="neutral" />
          )}
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: string | number; tone?: "neutral" | "good" | "warn" }) {
  return (
    <div className="rounded-2xl border border-white/12 bg-white/8 p-4 backdrop-blur">
      <div className="text-[11px] uppercase tracking-[0.18em] text-white/50">{label}</div>
      <div className={`mt-1 text-2xl font-black ${tone === "good" ? "text-[#14d87a]" : tone === "warn" ? "text-[#ffb000]" : "text-white"}`}>{value}</div>
    </div>
  );
}

function ActionPanel({ title, items, tone }: { title: string; tone: "violet" | "amber"; items: Array<{ href: string; title: string; meta: string }> }) {
  const accent = tone === "violet" ? "text-[#c7b7ff]" : "text-[#ffd28a]";
  return (
    <div className="premium-panel p-5 text-white">
      <h2 className={`text-lg font-black ${accent}`}>{title}</h2>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <Link key={item.href} href={item.href} className="block rounded-2xl border border-white/10 bg-white/8 p-3 transition-modern hover:bg-white/14">
            <div className="font-bold text-white">{item.title}</div>
            <div className="mt-1 text-xs text-white/55">{item.meta}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
