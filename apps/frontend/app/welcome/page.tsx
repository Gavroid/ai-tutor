/**
 * Sprint 104: Landing page (2026 design).
 *
 * Sections:
 * 1. Hero — bold typography + aurora gradient + glass CTA
 * 2. Features grid — 6 cards (subjects, AI tutor, parent dashboard, etc.)
 * 3. Stats — trust numbers (subjects, hours, students)
 * 4. CTA — gradient button
 */
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export const metadata = {
  title: "AI-Репетитор — Твой персональный учитель 7 класса",
  description: "Персональный AI-репетитор по всем предметам школьной программы. Адаптивный, безопасный, современный.",
};

const features = [
  {
    emoji: "🎓",
    title: "12 предметов",
    description: "Алгебра, геометрия, русский, литература, история, биология, физика и другие.",
    accent: "from-brand-500 to-purple-500",
  },
  {
    emoji: "🤖",
    title: "AI-объяснения",
    description: "Персональный репетитор объясняет тему, подстраиваясь под твой уровень и стиль обучения.",
    accent: "from-purple-500 to-pink-500",
  },
  {
    emoji: "📊",
    title: "Прогресс",
    description: "Отслеживай свои успехи, streak, сильные и слабые темы. Родители тоже видят статистику.",
    accent: "from-pink-500 to-red-500",
  },
  {
    emoji: "💙",
    title: "T1D-friendly",
    description: "Специальные паузы для замера глюкозы, спокойный дизайн, адаптация при гипо/гипер эпизодах.",
    accent: "from-cyan-500 to-blue-500",
  },
  {
    emoji: "🎤",
    title: "Голосовой ввод",
    description: "Отвечай голосом, получай озвученные объяснения. Удобно для мобильных устройств.",
    accent: "from-emerald-500 to-cyan-500",
  },
  {
    emoji: "👨‍👩‍👧",
    title: "Родительский контроль",
    description: "Родители видят прогресс, устанавливают лимиты, получают уведомления в Telegram.",
    accent: "from-amber-500 to-orange-500",
  },
];

const stats = [
  { value: "12", label: "предметов" },
  { value: "150+", label: "тем" },
  { value: "7", label: "учеников-пилотов" },
  { value: "100%", label: "T1D-friendly" },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-bg">
      {/* === Background aurora === */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-aurora"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-dots opacity-50"
      />

      {/* === Header === */}
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link href="/" className="flex items-center gap-2 font-display text-xl font-bold">
          <span className="text-2xl">🎓</span>
          <span>AI-Репетитор</span>
        </Link>
        <nav className="flex items-center gap-2">
          <Link href="/login">
            <Button variant="ghost" size="sm">Войти</Button>
          </Link>
          <Link href="/register">
            <Button variant="primary" size="sm">Регистрация</Button>
          </Link>
        </nav>
      </header>

      {/* === Hero === */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-20 text-center md:py-32">
        <Badge variant="brand" size="md" className="mx-auto mb-6 animate-fade-in">
          ✨ Персональный AI для 7 класса
        </Badge>

        <h1
          className="mx-auto max-w-4xl text-display-sm font-bold tracking-tight text-fg md:text-display-lg animate-slide-up"
          style={{ animationDelay: "100ms" }}
        >
          Учись в своём темпе,{" "}
          <span className="bg-gradient-to-br from-brand-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
            с AI-репетитором
          </span>
        </h1>

        <p
          className="mx-auto mt-6 max-w-2xl text-lg text-fg-muted md:text-xl animate-slide-up"
          style={{ animationDelay: "200ms" }}
        >
          Объясняет темы, проверяет задания, адаптируется под твой уровень.
          <br className="hidden md:block" />
          Создан для школьников с T1D — спокойно, безопасно, без спешки.
        </p>

        <div
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row animate-slide-up"
          style={{ animationDelay: "300ms" }}
        >
          <Link href="/register">
            <Button variant="primary" size="lg">
              Начать бесплатно
              <span aria-hidden>→</span>
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="outline" size="lg">
              У меня уже есть аккаунт
            </Button>
          </Link>
        </div>

        {/* Trust badge */}
        <p
          className="mt-8 text-sm text-fg-subtle animate-fade-in"
          style={{ animationDelay: "500ms" }}
        >
          🚀 7 учеников-пилотов уже учатся с AI-репетитором
        </p>
      </section>

      {/* === Features === */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-20">
        <div className="mb-12 text-center">
          <h2 className="text-display-sm font-bold tracking-tight text-fg">
            Всё что нужно для учёбы
          </h2>
          <p className="mt-3 text-lg text-fg-muted">
            Один инструмент — все предметы. С AI-помощником и родительским контролем.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <Card
              key={f.title}
              variant="elevated"
              padding="lg"
              interactive
              className="animate-slide-up"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div
                className={`mb-4 inline-flex size-12 items-center justify-center rounded-lg bg-gradient-to-br ${f.accent} text-2xl`}
                aria-hidden
              >
                {f.emoji}
              </div>
              <h3 className="mb-2 text-lg font-semibold text-fg">{f.title}</h3>
              <p className="text-sm text-fg-muted">{f.description}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* === Stats === */}
      <section className="relative z-10 mx-auto max-w-6xl px-6 py-20">
        <Card variant="glass" padding="xl" className="text-center">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label}>
                <div className="text-display-md font-bold text-brand-500">
                  {s.value}
                </div>
                <div className="mt-1 text-sm text-fg-muted">{s.label}</div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* === CTA === */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 py-20 text-center">
        <h2 className="text-display-sm font-bold tracking-tight text-fg">
          Готов попробовать?
        </h2>
        <p className="mt-3 text-lg text-fg-muted">
          Регистрация занимает 2 минуты. Первый урок — бесплатно.
        </p>
        <div className="mt-8">
          <Link href="/register">
            <Button variant="gradient" size="lg">
              Создать аккаунт
              <span aria-hidden>→</span>
            </Button>
          </Link>
        </div>
      </section>

      {/* === Footer === */}
      <footer className="relative z-10 border-t border-border py-8 text-center text-sm text-fg-subtle">
        <p>© 2026 AI-Репетитор. Создано с заботой для Кирилла и других учеников.</p>
      </footer>
    </main>
  );
}
