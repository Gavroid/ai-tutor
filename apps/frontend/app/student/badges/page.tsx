import Link from "next/link";
import StudentBadgesClient from "./client";

export default function StudentBadgesPage() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <header className="border-b border-slate-200 pb-4">
        <Link href="/subjects" className="text-sm text-sky-600 hover:underline">
          ← Все предметы
        </Link>
        <h1 className="mt-1 text-2xl font-bold">Мои достижения</h1>
        <p className="mt-1 text-sm text-slate-600">
          Баджи за усилие (не за streak). Получай их, пробуя новое и возвращаясь к сложному.
        </p>
      </header>
      <StudentBadgesClient />
    </main>
  );
}
