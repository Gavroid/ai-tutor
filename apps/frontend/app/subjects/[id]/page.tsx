"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { MathTopicPlan, Subject, Topic, User } from "@/types";
import Header from "@/components/Header";
import { StatusChip } from "@/components/StatusChip";

export default function SubjectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const subjectId = Number(params?.id);

  const [user, setUser] = useState<User | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [routePlan, setRoutePlan] = useState<MathTopicPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!subjectId || Number.isNaN(subjectId)) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (cancelled) return;
        setUser(me);
        const all = await api.subjects();
        if (cancelled) return;
        const currentSubject = all.find((x) => x.id === subjectId) ?? null;
        setSubject(currentSubject);
        if (!currentSubject) { setError("Предмет не найден"); return; }
        const [loadedTopics, loadedRoutePlan] = await Promise.all([
          api.subjectTopics(subjectId),
          api.subjectRoutePlan(subjectId).catch(() => []),
        ]);
        if (!cancelled) {
          setTopics(loadedTopics);
          setRoutePlan(loadedRoutePlan);
        }
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) { router.push("/login"); return; }
        setError("Не удалось загрузить темы. Проверь соединение и попробуй ещё раз.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [subjectId, router]);

  const routeByTopic = new Map(routePlan.map((item) => [item.topic_id, item]));
  const routeSummary = {
    base: routePlan.filter((item) => item.tier === "base").length,
    medium: routePlan.filter((item) => item.tier === "medium").length,
    hard: routePlan.filter((item) => item.tier === "hard").length,
    checkpoints: routePlan.filter((item) => item.checkpoint).length,
  };
  // Sprint 2026-08-22: блокируем навигацию ребёнка в non-pilot предмет.
  // Teacher/admin по-прежнему могут видеть темы и route plan, но видят явный баннер.
  const isOperator = user?.role === "teacher" || user?.role === "admin";
  const canStudentEnter = subject?.pilot_visible === true;
  const showStudentGate = subject && !isOperator && !canStudentEnter;

  if (showStudentGate) {
    return (
      <main className="prism-shell">
        <Header user={user} backHref="/subjects" backLabel="Все предметы" title={subject ? `${subject.icon || "📘"} ${subject.name}` : "Предмет"} />
        <section className="py-3 sm:py-5">
          <div className="prism-frame">
            <div className="prism-layer px-4 pb-7 lg:px-7">
              <div className="prism-card pad">
                <div className="prism-kicker">Subject locked</div>
                <h1 className="prism-title mt-3">
                  <span className="accent">{subject?.icon || "📘"}</span> {subject?.name || "Предмет"} — в обработке
                </h1>
                <p className="mt-4 max-w-2xl text-sm text-[color:var(--prism-muted)]">
                  Этот предмет пока проходит evidence-проверку (манифест, разметка страниц, импорт,
                  retrieval probes, ручной smoke). Ребёнку доступны только пилотные предметы,
                  которые прошли все шесть шагов проверки.
                </p>
                <p className="mt-3 max-w-2xl text-sm text-[color:var(--prism-muted)]">
                  Сейчас пилот — математика 6 класса. Возвращайся в каталог и выбирай её,
                  либо спроси родителя, когда этот предмет будет готов.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link href="/subjects" className="prism-action primary">← В каталог предметов</Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="prism-shell">
      {/* Sprint 3.9.7.5: Header.tsx автоматически добавляет префикс «← »,
          поэтому в backLabel только текст, без стрелки. */}
      <Header user={user} backHref="/subjects" backLabel="Все предметы" title={subject ? `${subject.icon || "📘"} ${subject.name}` : "Предмет"} />
      <section className="py-3 sm:py-5">
        <div className="prism-frame">
          {/* Sprint 3.9.7.6: prism-hero-grid → одна колонка на всю ширину.
              Раньше было 2 колонки (1.05fr | 360px min) — на длинных названиях
              предмета (например «Математика (6 класс - повторение пройденного материала)»)
              правая колонка вылезала за hero и обрезалась.
              Readiness Panel унесён в отдельную секцию ниже. */}
          <div className="prism-layer prism-hero-grid subject-compact-hero">
            <section>
              <div className="prism-kicker">Subject Object · Route Map</div>
              {/* Sprint 3.9.7.6: разделяем название по скобкам — основная часть в <h1>,
                  подзаголовок в скобках в <p> под ним. Если скобок нет —
                  показываем весь текст в <h1>. */}
              {(() => {
                const fullName = subject?.name || "Загружаем";
                const match = /^(.*?)\s*\((.+)\)\s*$/.exec(fullName);
                if (match) {
                  const [, main, sub] = match;
                  return (
                    <>
                      <h1 className="prism-title subject-title-wide">
                        <span className="accent">{subject?.icon || "📘"}</span> {main.trim()}
                      </h1>
                      <p className="prism-title-subtitle">{sub.trim()}</p>
                    </>
                  );
                }
                return (
                  <h1 className="prism-title subject-title-wide">
                    <span className="accent">{subject?.icon || "📘"}</span> {fullName}
                  </h1>
                );
              })()}
              {subject?.description && <p className="prism-copy">{subject.description}</p>}
            </section>
          </div>

          {/* Sprint 3.9.7.5: Readiness Panel вынесен из правого сайдбара в
              отдельную полноширинную секцию — пользователь сказал
              «растянуть по ширине экрана чтобы убрать пустоты». */}
          <section className="prism-card pad glow mt-4 mx-4 lg:mx-7">
            <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">Readiness Panel</div>
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <Readiness label="Тем" value={topics.length || "—"} />
              <Readiness label="Статус" value={statusLabelFor(subject?.mvp_status ?? "preview")} />
              <Readiness label="RAG" value={subject?.rag_ready ? "ON" : "OFF"} hot={!!subject?.rag_ready} />
              <Readiness label="Practice" value={subject?.practice_ready ? "ON" : "Preview"} hot={!!subject?.practice_ready} />
              {routePlan.length > 0 && (
                <Readiness
                  label="Маршрут"
                  value={`${routePlan.length}/${routePlan.length}`}
                  hot
                />
              )}
              {routePlan.length > 0 && <Readiness label="Контроль" value={routeSummary.checkpoints} hot />}
            </div>
            {isOperator && (
              <div className="mt-4 rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/40 p-3 text-[10px] uppercase tracking-[0.14em]">
                <div className="text-[color:var(--prism-muted)]">Evidence gates (оператор)</div>
                <div className="mt-2 grid grid-cols-2 gap-1 sm:grid-cols-3 lg:grid-cols-6">
                  <EvidenceBadge label="manifest" ready={!!subject?.manifest_ready} />
                  <EvidenceBadge label="mapping" ready={!!subject?.mapping_ready} />
                  <EvidenceBadge label="import" ready={!!subject?.import_ready} />
                  <EvidenceBadge label="rag" ready={!!subject?.rag_ready} />
                  <EvidenceBadge label="practice" ready={!!subject?.practice_ready} />
                  <EvidenceBadge label="smoke" ready={!!subject?.manual_smoke_ready} />
                </div>
                <div className={`mt-3 text-center font-black ${subject?.pilot_visible ? "text-[color:var(--prism-green)]" : "text-[color:var(--prism-amber)]"}`}>
                  {subject?.pilot_visible ? "✓ pilot-visible для ребёнка" : "✗ скрыт от ребёнка"}
                </div>
              </div>
            )}
            {subject && (
              <p className="mt-5 rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/45 p-4 text-sm text-[color:var(--prism-muted)]">
                <b>{subject.mvp_status === "mvp_ready" ? "MVP-ready." : "Preview-предмет."}</b> {subject.support_note}
              </p>
            )}
          </section>

          <section className="prism-layer px-4 pb-5 lg:px-7 lg:pb-7">
            {loading && <div className="prism-card pad">Загружаем темы…</div>}
            {error && !loading && <div className="prism-card pad text-danger">{error}</div>}
            {!loading && !error && topics.length === 0 && <div className="prism-card pad">В этом предмете пока нет тем.</div>}

            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="prism-kicker">Timeline</div>
                <h2 className="mt-2 text-3xl font-black tracking-[-0.05em] sm:text-5xl">Маршрут тем</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusChip
                  status={(subject?.mvp_status ?? "preview") as never}
                  blockedReason={subject?.blocked_reason ?? null}
                  pilotVisible={!!subject?.pilot_visible}
                  size="md"
                />
                {routePlan.length > 0 && <span className="prism-pill active">Base {routeSummary.base} · Medium {routeSummary.medium} · Hard {routeSummary.hard}</span>}
              </div>
            </div>

            <ol className="grid gap-3 xl:grid-cols-2">
              {topics.map((topic, index) => {
                const route = routeByTopic.get(topic.id);
                return (
                <li key={topic.id}>
                  <Link href={`/topics/${topic.id}`} className="prism-card pad flex min-h-[124px] flex-col gap-3 hover:border-[color:var(--prism-accent)] sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-start gap-4">
                      <span className="prism-mark flex shrink-0 items-center justify-center text-sm font-black text-white">{String(route?.order ?? index + 1).padStart(2, "0")}</span>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-lg font-black tracking-[-0.035em]">{topic.name}</h3>
                          {route?.checkpoint && <span className="prism-pill active">Контроль</span>}
                        </div>
                        {route?.focus && <p className="mt-1 text-sm text-[color:var(--prism-muted)]">Фокус: {route.focus}</p>}
                        {topic.description && <p className="mt-1 line-clamp-2 text-sm text-[color:var(--prism-muted)]">{topic.description}</p>}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 sm:justify-end">
                      {route?.tier && <span className="prism-pill">{route.tier}</span>}
                      <span className="prism-pill">{topic.difficulty}/5</span>
                    </div>
                  </Link>
                </li>
              );})}
            </ol>
          </section>
        </div>
      </section>
    </main>
  );
}

function Readiness({ label, value, hot = false }: { label: string; value: string | number; hot?: boolean }) {
  return <div className="rounded-3xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/50 p-4"><div className="text-[10px] font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">{label}</div><div className={`mt-1 text-2xl font-black ${hot ? "text-[color:var(--prism-green)]" : ""}`}>{value}</div></div>;
}

function statusLabelFor(status: string): string {
  switch (status) {
    case "mvp_ready":
      return "Ready";
    case "internal_mvp":
      return "В обработке";
    case "blocked_ocr":
      return "OCR-blocked";
    case "not_available":
      return "Недоступно";
    case "preview":
    default:
      return "Preview";
  }
}

function EvidenceBadge({ label, ready }: { label: string; ready: boolean }) {
  return (
    <span
      className={`rounded-md border px-1.5 py-0.5 text-center ${
        ready
          ? "border-[color:var(--prism-green)]/40 text-[color:var(--prism-green)]"
          : "border-[color:var(--prism-line)] text-[color:var(--prism-muted)]"
      }`}
      title={`${label}: ${ready ? "yes" : "no"}`}
    >
      {ready ? "✓" : "·"} {label}
    </span>
  );
}
