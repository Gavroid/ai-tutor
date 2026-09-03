"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Subject, User } from "@/types";
import EmptyState from "@/components/EmptyState";
import Header from "@/components/Header";
import { StatusChip, statusLabelFor as statusLabelForChip } from "@/components/StatusChip";

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
  // Sprint 2026-08-22: для роли student показываем только pilot_visible=true.
  // Для teacher/admin/parent — все subjects, чтобы они могли видеть pipeline status.
  const isOperator = user?.role === "teacher" || user?.role === "admin";
  const visibleSubjects = isOperator
    ? subjects
    : subjects.filter((s) => s.pilot_visible === true);
  const filtered = q
    ? visibleSubjects.filter(
        (s) => s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q)
      )
    : visibleSubjects;
  const readyCount = subjects.filter((s) => s.mvp_status === "mvp_ready").length;
  const pilotVisibleCount = subjects.filter((s) => s.pilot_visible === true).length;
  const blockedCount = subjects.filter((s) => s.mvp_status === "blocked_ocr").length;
  const previewCount = Math.max(subjects.length - readyCount - blockedCount, 0);

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

            <aside className="prism-card pad glow flex flex-col">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">Live System</div>
              {/* Sprint 3.16: расширяем блок, чтобы закрыть пустоту снизу (filler + flex-grow). */}
              <div className="mt-4 grid grid-cols-2 gap-2 flex-1 content-start">
                <Metric label="Предметов" value={subjects.length || "—"} />
                <Metric label="Пилот" value={pilotVisibleCount || "—"} hot={pilotVisibleCount > 0} />
                <Metric label="В обработке" value={previewCount || "—"} />
                <Metric label="OCR-blocked" value={blockedCount || "—"} />
                <Metric label="AI" value={aiOk === null ? "…" : aiOk ? "ON" : "OFF"} hot={!!aiOk} />
              </div>
              {/* Sprint 3.16: убрали текст «Ребёнку показываются только пилотные предметы»
                  — для ребёнка/родителя это внутренняя кухня pilot-scope, ничего полезного. */}
              {/* Sprint 3.9.7.3: убрал «Режим оператора: видны все subjects» —
                  это техническая деталь для разработчика, не для ребёнка/родителя.
                  Сейчас её и так нет в production-ветке (только для admin). */}
              {/* Sprint 3.9.7.3: убрал «Модель: openai/gpt-5.6-luna» —
                  для ребёнка это техническая информация, которая его отвлекает.
                  Модель видна только в /admin/ai-providers (Sprint 3.9.6). */}
              {/* Sprint 3.9.7.7 (revised): блок «Стоит повторить» был вынесен
                  из правого сайдбара (Sprint 3.9.7.3), но лежал ВНУТРИ
                  prism-hero-grid → контейнер ~50% ширины → карточки в 2 ряда.
                  Теперь он вынесен НАРУЖУ (после </div> prism-layer), на полную
                  ширину prism-frame — карточки одной строкой. */}
            </aside>
          </div>

          {/* Sprint 3.9.7.7 (revised): блок «Стоит повторить» вынесен ИЗ
              prism-hero-grid наружу — раньше он лежал внутри hero-grid
              (grid 2 колонки) и контейнер был ~50% ширины, поэтому
              grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))
              давал только 2 колонки в строке (5×220 не помещалось).
              Теперь блок на всю ширину prism-frame — все 5 карточек
              в одну строку. */}
          <section className="prism-card pad glow mt-4 mx-4 lg:mx-7">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[color:var(--prism-muted)]">
                Стоит повторить
              </div>
              {review.length > 0 && (
                <div className="text-xs text-[color:var(--prism-muted)]">
                  Показано: {Math.min(review.length, 6)} из {review.length}
                </div>
              )}
            </div>
            {review.length > 0 ? (
              <div
                className="grid gap-3"
                style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}
              >
                {review.slice(0, 6).map((r) => (
                  <Link
                    key={r.topic_id}
                    href={`/topics/${r.topic_id}`}
                    className="prism-review-row block rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/40 px-4 py-3 hover:border-[color:var(--prism-accent)] transition-colors"
                  >
                    <div className="truncate text-base font-black">{r.topic_name}</div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-[color:var(--prism-muted)]">
                      <span>Уверенность {Math.round(r.mastery_score * 100)}%</span>
                      {r.subject_name && (
                        <>
                          <span aria-hidden="true">·</span>
                          <span className="truncate">{r.subject_name}</span>
                        </>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[color:var(--prism-muted)]">
                Пока нечего повторять — начни урок или диагностику.
              </p>
            )}
          </section>


          <section className="prism-layer px-4 pb-5 lg:px-7 lg:pb-7">
            <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_360px] lg:items-end">
              <div>
                {/* Sprint 3.16: убрали «Subject Gallery» kicker — лишний заголовок перед Каталогом. */}
                <h2 className="text-3xl font-black tracking-[-0.05em] sm:text-5xl">
                  {isOperator ? "Каталог предметов · оператор" : "Каталог предметов"}
                </h2>
                <p className="mt-2 max-w-2xl text-sm text-[color:var(--prism-muted)]">
                  {isOperator
                    ? "Видны все subjects и их evidence-статусы. Только pilot_visible=true показывается ребёнку."
                    : "Доступны только предметы, прошедшие полную evidence-проверку и помеченные pilot_visible."}
                </p>
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
                {filtered.map((s) => {
                  const status = s.mvp_status ?? "preview";
                  const statusLabel = statusLabelFor(status);
                  return (
                    <Link key={s.id} href={`/subjects/${s.id}`} className="prism-card prism-subject-card">
                      <div className="flex items-start justify-between gap-4">
                        <div className="prism-mark flex items-center justify-center text-2xl text-white">{s.icon || "📘"}</div>
                        <div className="flex flex-col items-end gap-1">
                          {/* Sprint H2.4: реальный статус через StatusChip, не "MVP-ready" для всех. */}
                          <StatusChip
                            status={status as never}
                            blockedReason={s.blocked_reason ?? null}
                            pilotVisible={s.pilot_visible ?? false}
                            size="sm"
                          />
                          {isOperator && (
                            <span className={`text-[10px] font-black uppercase tracking-[0.14em] ${s.pilot_visible ? "text-[color:var(--prism-green)]" : "text-[color:var(--prism-muted)]"}`}>
                              {s.pilot_visible ? "pilot ✓" : "скрыт от ребёнка"}
                            </span>
                          )}
                        </div>
                      </div>
                      <h3 className="mt-6 text-3xl font-black tracking-[-0.04em]">{s.name}</h3>
                      {s.description && <p className="mt-3 line-clamp-3 text-sm text-[color:var(--prism-muted)]">{s.description}</p>}
                      <p className="mt-5 text-xs leading-relaxed text-[color:var(--prism-muted)]">{s.support_note}</p>
                      <div className="mt-5 grid gap-2 text-xs">
                        <ReadinessLine label="Маршрут" ready={!!s.route_ready} value={`${s.route_topic_count ?? 0}/${s.topic_count ?? 0}`} />
                        <ReadinessLine label="Источники" ready={!!s.rag_ready} value={`${s.source_topic_count ?? 0}/${s.topic_count ?? 0}`} />
                        <ReadinessLine label="Практика" ready={!!s.practice_ready} value={`${s.practice_topic_count ?? 0}/${s.topic_count ?? 0}`} />
                      </div>
                      {isOperator && (
                        <div className="mt-3 grid grid-cols-3 gap-1 text-[10px] uppercase tracking-[0.12em]">
                          <EvidenceBadge label="manifest" ready={!!s.manifest_ready} />
                          <EvidenceBadge label="mapping" ready={!!s.mapping_ready} />
                          <EvidenceBadge label="import" ready={!!s.import_ready} />
                        </div>
                      )}
                      <div className="mt-6 flex items-center justify-between border-t border-[color:var(--prism-line)] pt-4 text-xs font-black uppercase tracking-[0.16em]">
                        <span>{s.recommended_grade} класс</span><span>Открыть →</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <EmptyState
                icon="🔍"
                title={isOperator ? "Ничего не найдено по запросу" : "Доступных предметов пока нет"}
                description={
                  isOperator
                    ? "Попробуй другой запрос, например: матем, русск, физика"
                    : "Пилотный предмет проходит финальную проверку. Скоро здесь появится."
                }
                variant="neutral"
              />
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function ReadinessLine({ label, ready, value }: { label: string; ready: boolean; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-[color:var(--prism-line)] bg-[color:var(--prism-panel-solid)]/35 px-3 py-2">
      <span className="font-black uppercase tracking-[0.14em] text-[color:var(--prism-muted)]">{label}</span>
      <span className={ready ? "font-black text-[color:var(--prism-green)]" : "font-black text-[color:var(--prism-amber)]"}>{value}</span>
    </div>
  );
}

function statusLabelFor(status: string): string {
  switch (status) {
    case "mvp_ready":
      return "MVP-ready";
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
