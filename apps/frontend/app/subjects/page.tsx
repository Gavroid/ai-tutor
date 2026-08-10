"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Subject, User } from "@/types";
import EmptyState from "@/components/EmptyState";
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
  const [dueReview, setDueReview] = useState<Array<{ topic_id: number; topic_name: string; subject_name: string; mastery_score: number; days_overdue: number }>>([]);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    api.me().then(setUser).catch((err: unknown) => {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) router.push("/login");
      else console.warn("api.me() failed (non-auth):", err);
    });
    api.subjects().then(setSubjects).catch(() => {});
    api.aiPing().then((r) => { setAiOk(r.ok); setAiModel(r.model); }).catch(() => setAiOk(false));
    api.recommendReview().then(setReview).catch(() => {});
    api.dueForReview(10).then(setDueReview).catch(() => {});
  }, [router]);

  const q = searchQuery.trim().toLowerCase();
  const filtered = q ? subjects.filter((s) => s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q)) : subjects;
  const readyCount = subjects.filter((s) => s.mvp_status === "mvp_ready").length;
  const previewCount = Math.max(subjects.length - readyCount, 0);

  return (
    <main className="prism-shell">
      <Header user={user} title="Prism Learning OS" />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          <div className="prism-layer prism-hero-grid">
            <section>
              <div className="prism-kicker">Explore · Student Mission Control</div>
              <h1 className="prism-title">Выбери <span className="accent">траекторию</span> обучения</h1>
              <p className="prism-copy">
                Не лента предметов, а рабочая карта: готовые темы, повторение, слабые места и понятный следующий шаг в одном экране.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link href="/diagnostic" className="prism-action primary">Диагностика</Link>
                <Link href="/link-parent" className="prism-action">Привязать родителя</Link>
                {user?.role === "parent" && <Link href="/parents" className="prism-action">Родительский кабинет</Link>}
                {(user?.role === "teacher" || user?.role === "admin") && <Link href="/teacher" className="prism-action">Учительская</Link>}
                {user?.role === "admin" && <Link href="/admin" className="prism-action">Админ</Link>}
              </div>
            </section>

            <aside className="prism-card pad glow">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">Live System</div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Metric label="Предметов" value={subjects.length || "—"} />
                <Metric label="MVP-ready" value={readyCount || "—"} />
                <Metric label="Preview" value={previewCount || "—"} />
                <Metric label="AI" value={aiOk === null ? "…" : aiOk ? "ON" : "OFF"} hot={!!aiOk} />
              </div>
              {aiOk === true && aiModel && <p className="mt-4 text-xs text-[color:var(--prism-muted)]">Модель: {aiModel}</p>}
              <div className="prism-orb relative mt-4 min-h-[160px]" aria-hidden="true" />
            </aside>
          </div>

          {(dueReview.length > 0 || review.length > 0) && (
            <div className="prism-layer grid gap-3 px-4 pb-4 lg:grid-cols-2 lg:px-7">
              {dueReview.length > 0 && <ActionPanel title="Сегодня к повторению" items={dueReview.slice(0, 4).map((d) => ({ href: `/topics/${d.topic_id}`, title: d.topic_name, meta: `${d.subject_name} · ${d.days_overdue > 0 ? `просрочено ${d.days_overdue}д` : "сегодня"}` }))} />}
              {review.length > 0 && <ActionPanel title="Стоит повторить" items={review.slice(0, 4).map((r) => ({ href: `/topics/${r.topic_id}`, title: r.topic_name, meta: `${r.subject_name} · уверенность ${Math.round(r.mastery_score * 100)}%` }))} />}
            </div>
          )}

          <section className="prism-layer px-4 pb-5 lg:px-7 lg:pb-7">
            <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_360px] lg:items-end">
              <div>
                <div className="prism-kicker">Subject Gallery</div>
                <h2 className="mt-2 text-3xl font-black tracking-[-0.05em] sm:text-5xl">Каталог предметов</h2>
                <p className="mt-2 max-w-2xl text-sm text-[color:var(--prism-muted)]">MVP-ready — можно тестировать полноценно. Preview — виден в системе, но без обещания качества источников и практики.</p>
              </div>
              <input
                type="search"
                inputMode="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск: математика, русский, физика…"
                className="prism-input"
              />
            </div>

            {filtered.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {filtered.map((s) => (
                  <Link key={s.id} href={`/subjects/${s.id}`} className={`prism-card prism-subject-card ${s.mvp_status === "mvp_ready" ? "xl:col-span-2" : ""}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="prism-mark flex items-center justify-center text-2xl text-white">{s.icon || "📘"}</div>
                      <span className={`prism-pill ${s.mvp_status === "mvp_ready" ? "active" : ""}`}>{s.mvp_status === "mvp_ready" ? "MVP-ready" : "Preview"}</span>
                    </div>
                    <h3 className="mt-6 text-3xl font-black tracking-[-0.04em]">{s.name}</h3>
                    {s.description && <p className="mt-3 line-clamp-3 text-sm text-[color:var(--prism-muted)]">{s.description}</p>}
                    <p className="mt-5 text-xs leading-relaxed text-[color:var(--prism-muted)]">{s.support_note}</p>
                    <div className="mt-6 flex items-center justify-between border-t border-[color:var(--prism-line)] pt-4 text-xs font-black uppercase tracking-[0.16em]">
                      <span>7 класс</span><span>Открыть →</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState icon="🔍" title={`Ничего не найдено по «${searchQuery}»`} description="Попробуй другой запрос, например: матем, русск, физика" variant="neutral" />
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value, hot = false }: { label: string; value: string | number; hot?: boolean }) {
  return (
    <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4">
      <div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div>
      <div className={`mt-1 text-3xl font-black ${hot ? "text-[color:var(--prism-green)]" : ""}`}>{value}</div>
    </div>
  );
}

function ActionPanel({ title, items }: { title: string; items: Array<{ href: string; title: string; meta: string }> }) {
  return (
    <div className="prism-card pad">
      <h2 className="text-xl font-black">{title}</h2>
      <div className="mt-4 grid gap-2">
        {items.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/55 p-3 hover:border-[color:var(--prism-accent)]">
            <div className="font-black">{item.title}</div>
            <div className="mt-1 text-xs text-[color:var(--prism-muted)]">{item.meta}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
