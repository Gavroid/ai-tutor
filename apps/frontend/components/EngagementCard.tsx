"use client";

interface EngagementData {
  period_days: number;
  active_users: number;
  total_attempts: number;
  avg_attempts_per_active_user: number;
  dau_last_14_days: Array<{ date: string; active_users: number }>;
  top_subjects: Array<{ id: number; name: string; students: number }>;
}

interface EngagementCardProps {
  data: EngagementData;
}

/**
 * Sprint 9 — карточка engagement для админ-панели.
 * Показывает DAU за 14 дней (bar chart на CSS), active users, total attempts.
 */
export default function EngagementCard({ data }: EngagementCardProps) {
  const maxDau = Math.max(1, ...data.dau_last_14_days.map((d) => d.active_users));

  return (
    <div
      data-testid="engagement-card"
      className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div>
        <h2 className="text-lg font-bold text-slate-900">📊 Активность за {data.period_days} дней</h2>
        <p className="text-xs text-slate-500">Метрики engagement для админа</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="Активных" value={data.active_users} />
        <Kpi label="Всего попыток" value={data.total_attempts} />
        <Kpi
          label="Среднее на юзера"
          value={data.avg_attempts_per_active_user}
          decimals={1}
        />
        <Kpi
          label="Топ предметов"
          value={data.top_subjects.length}
          suffix={`/${data.top_subjects.length || 0}`}
        />
      </div>

      {/* DAU bar chart (14 days) */}
      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">
          📅 Активные пользователи по дням (14 дней)
        </h3>
        <div className="flex h-32 items-end gap-1">
          {data.dau_last_14_days.map((d) => {
            const height = (d.active_users / maxDau) * 100;
            const dateLabel = d.date.slice(5); // MM-DD
            return (
              <div
                key={d.date}
                className="group relative flex flex-1 flex-col items-center justify-end"
                title={`${d.date}: ${d.active_users} active`}
              >
                <div
                  className="w-full rounded-t bg-sky-500 transition-all group-hover:bg-sky-600"
                  style={{ height: `${Math.max(height, 2)}%` }}
                />
                <div className="absolute -top-6 hidden rounded bg-slate-900 px-1.5 py-0.5 text-[10px] text-white group-hover:block">
                  {d.active_users}
                </div>
                <div className="mt-1 text-[9px] text-slate-500">{dateLabel}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top subjects */}
      {data.top_subjects.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">🏆 Топ предметы</h3>
          <div className="space-y-1">
            {data.top_subjects.map((s, idx) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm"
              >
                <span className="flex items-center gap-2">
                  <span className="text-base font-bold text-sky-600">#{idx + 1}</span>
                  <span className="text-slate-900">{s.name}</span>
                </span>
                <span className="text-xs text-slate-500">{s.students} учеников</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  decimals = 0,
  suffix,
}: {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
}) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-slate-900">
        {value.toFixed(decimals)}
        {suffix && <span className="ml-1 text-sm font-normal text-slate-500">{suffix}</span>}
      </div>
    </div>
  );
}