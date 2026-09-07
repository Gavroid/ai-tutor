"use client";

// Sprint 4 RAG production: admin UI для batch PDF ingestion.
//
// Дизайн (как у /admin/ai-providers): prism-shell + prism-frame + prism-card.
// 3 секции:
// 1. Upload — drag-and-drop / file picker, subject auto-detect, dry-run checkbox.
// 2. Reindex — список materials с кнопкой reindex (full_wipe|skip_existing).
// 3. Stats — chunks_total, jobs_24h, p50/p95 latency, queue depth, embedding mode.
//
// Использует api.get/post (single-source).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Header from "@/components/Header";
import { api, ApiError } from "@/lib/api";

// ----- Types (mirror backend rag_schemas.py) -----

type JobStatus = "queued" | "running" | "done" | "failed";

type IngestResponse = {
  job_id: string;
  status: JobStatus;
  material_id: number;
  chunks_count: number;
  duration_ms: number | null;
  message: string | null;
};

type RagJobStatus = {
  job_id: string;
  status: JobStatus;
  material_id: number | null;
  chunks_count: number;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type RagStats = {
  jobs_last_24h: number;
  jobs_failed: number;
  chunks_total: number;
  avg_duration_ms: number;
  p50_duration_ms: number;
  p95_duration_ms: number;
  queue_depth: number;
  embedding_mode: string; // "real" | "hash_fallback"
};

type Subject = { id: number; code: string; name: string };

// ----- API helpers (single-source через lib/api.ts) -----

const ragApi = {
  upload: (file: File, materialId: number, filename: string, dryRun: boolean) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("filename", filename);
    fd.append("material_id", String(materialId));
    if (dryRun) fd.append("dry_run", "true");
    return fetch(
      `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/admin/rag/upload`,
      {
        method: "POST",
        body: fd,
        credentials: "include",
      },
    ).then(async (r) => {
      const text = await r.text();
      let body: unknown = text;
      try {
        body = JSON.parse(text);
      } catch {
        /* not JSON */
      }
      if (!r.ok) {
        const msg =
          body && typeof body === "object" && "detail" in body
            ? String((body as { detail: unknown }).detail)
            : `HTTP ${r.status}`;
        throw new ApiError(r.status, { detail: msg });
      }
      return body as IngestResponse;
    });
  },
  status: (jobId: string) => api.get<RagJobStatus>(`/api/v1/admin/rag/status?job_id=${jobId}`),
  stats: () => api.get<RagStats>("/api/v1/admin/rag/stats"),
  reindex: (materialId: number, mode: "full_wipe" | "skip_existing", filename: string) =>
    api.post<IngestResponse>("/api/v1/admin/rag/reindex", {
      material_id: materialId,
      mode,
      filename,
    }),
  listSubjects: () => api.get<Subject[]>("/api/v1/subjects"),
};

// ----- Subject detection (mirror backend regex) -----

function detectSubject(filename: string): { code: string | null; grade: number | null } {
  const fname = filename.toLowerCase().replace(/\.pdf$/i, "");
  // Match: code[-_]?grade? at start of filename.
  const m = /^([a-zа-яё]+)(?:[_-](\d{1,2}))?/i.exec(fname);
  if (!m) return { code: null, grade: null };
  const codeRaw = m[1].toLowerCase();
  const gradeStr = m[2] || null;
  // Fallback: если grade не сразу за code, ищем в хвосте.
  let grade = gradeStr ? Number(gradeStr) : null;
  if (grade === null) {
    const tail = fname.slice(m[0].length);
    const m2 = /[_-](\d{1,2})$/.exec(tail);
    if (m2) grade = Number(m2[1]);
  }
  // Known subject codes.
  const known: Record<string, string> = {
    math: "math",
    mathematics: "math",
    algebra: "math",
    geometria: "math",
    russian: "russian",
    physics: "physics",
    chemistry: "chemistry",
    biology: "biology",
    history: "history",
    english: "english",
    informatics: "informatics",
  };
  return { code: known[codeRaw] || null, grade };
}

// ----- Page component -----

export default function AdminRagPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [stats, setStats] = useState<RagStats | null>(null);
  const [lastJob, setLastJob] = useState<IngestResponse | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [detectedSubject, setDetectedSubject] = useState<{
    code: string | null;
    grade: number | null;
  } | null>(null);
  const [manualSubject, setManualSubject] = useState<string>("");
  const [materialIdInput, setMaterialIdInput] = useState<string>("1");
  const [reindexMaterialId, setReindexMaterialId] = useState<string>("1");
  const [reindexMode, setReindexMode] = useState<"full_wipe" | "skip_existing">("full_wipe");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load stats + subjects on mount.
  const refresh = useCallback(async () => {
    try {
      const [s, sub] = await Promise.all([
        ragApi.stats().catch(() => null),
        ragApi.listSubjects().catch(() => []),
      ]);
      if (s) setStats(s);
      if (Array.isArray(sub)) setSubjects(sub);
    } catch (err) {
      console.error("Sprint 4 RAG: refresh failed", err);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // File picker handler.
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setPendingFile(file);
    setLastJob(null);
    setLastError(null);
    if (file) {
      const det = detectSubject(file.name);
      setDetectedSubject(det);
      setManualSubject(det.code || "");
    }
  };

  // Upload handler.
  const onUpload = async () => {
    if (!pendingFile) return;
    setUploading(true);
    setLastError(null);
    try {
      const result = await ragApi.upload(
        pendingFile,
        Number(materialIdInput),
        pendingFile.name,
        dryRun,
      );
      setLastJob(result);
      // Auto-refresh stats after a moment.
      setTimeout(refresh, 1500);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      setLastError(msg);
    } finally {
      setUploading(false);
      // Reset file input.
      if (fileInputRef.current) fileInputRef.current.value = "";
      setPendingFile(null);
    }
  };

  // Reindex handler.
  const onReindex = async () => {
    setLastError(null);
    try {
      const result = await ragApi.reindex(
        Number(reindexMaterialId),
        reindexMode,
        "reindex.pdf",
      );
      setLastJob(result);
      setTimeout(refresh, 1500);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      setLastError(msg);
    }
  };

  const embeddingBadge = useMemo(() => {
    if (!stats) return "—";
    return stats.embedding_mode === "real"
      ? "Real (sentence-transformers)"
      : "Hash fallback";
  }, [stats]);

  return (
    <div className="prism-shell min-h-screen">
      <Header user={null} backHref="/admin" title="RAG ingestion" />
      <main className="prism-frame mx-auto max-w-6xl px-4 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-100">
            Sprint 4 RAG — admin ingestion
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Загрузка PDF в RAG-индекс. Auto-detect subject, async через Redis queue
            (или sync fallback если Redis недоступен).
          </p>
        </header>

        {/* === Section 1: Upload === */}
        <section className="prism-card mb-6 p-5">
          <h2 className="mb-3 text-lg font-medium text-slate-100">
            1. Загрузить PDF
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm text-slate-300">PDF файл</span>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                onChange={onFileChange}
                className="mt-1 block w-full text-sm text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-sky-700 file:px-3 file:py-2 file:text-white hover:file:bg-sky-600"
              />
            </label>
            <label className="block">
              <span className="text-sm text-slate-300">Material ID</span>
              <input
                type="number"
                min="1"
                value={materialIdInput}
                onChange={(e) => setMaterialIdInput(e.target.value)}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
              />
            </label>
            <div className="sm:col-span-2">
              {pendingFile && (
                <div className="rounded border border-slate-700 bg-slate-800/60 p-3 text-sm">
                  <div className="text-slate-300">
                    Файл: <span className="font-mono">{pendingFile.name}</span>{" "}
                    ({(pendingFile.size / 1024).toFixed(1)} KB)
                  </div>
                  {detectedSubject && (
                    <div className="mt-1 text-slate-400">
                      Auto-detect:{" "}
                      <span className="font-mono text-sky-300">
                        {detectedSubject.code || "(unknown)"}{" "}
                        {detectedSubject.grade ? `grade ${detectedSubject.grade}` : ""}
                      </span>{" "}
                      (override:{" "}
                      <select
                        value={manualSubject}
                        onChange={(e) => setManualSubject(e.target.value)}
                        className="ml-1 rounded border border-slate-700 bg-slate-900 px-1 py-0.5 text-xs text-slate-200"
                      >
                        <option value="">—</option>
                        {subjects.map((s) => (
                          <option key={s.id} value={s.code}>
                            {s.code} ({s.name})
                          </option>
                        ))}
                      </select>
                      )
                    </div>
                  )}
                </div>
              )}
              <label className="mt-3 inline-flex items-center gap-2 text-sm text-slate-300">
                <input
                  type="checkbox"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  className="rounded"
                />
                Dry-run (не писать в rag_chunks)
              </label>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={onUpload}
              disabled={!pendingFile || uploading}
              className="prism-action rounded bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-50"
            >
              {uploading ? "Загрузка…" : "Upload"}
            </button>
          </div>
        </section>

        {/* === Section 2: Reindex === */}
        <section className="prism-card mb-6 p-5">
          <h2 className="mb-3 text-lg font-medium text-slate-100">
            2. Reindex существующего материала
          </h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="text-sm text-slate-300">Material ID</span>
              <input
                type="number"
                min="1"
                value={reindexMaterialId}
                onChange={(e) => setReindexMaterialId(e.target.value)}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
              />
            </label>
            <label className="block">
              <span className="text-sm text-slate-300">Mode</span>
              <select
                value={reindexMode}
                onChange={(e) =>
                  setReindexMode(e.target.value as "full_wipe" | "skip_existing")
                }
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
              >
                <option value="full_wipe">full_wipe (DELETE + re-ingest)</option>
                <option value="skip_existing">skip_existing (idempotent)</option>
              </select>
            </label>
            <div className="flex items-end">
              <button
                type="button"
                onClick={onReindex}
                className="prism-action rounded bg-amber-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-amber-500"
              >
                Reindex
              </button>
            </div>
          </div>
        </section>

        {/* === Section 3: Stats === */}
        <section className="prism-card mb-6 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-medium text-slate-100">
              3. Monitoring (последние 24h)
            </h2>
            <button
              type="button"
              onClick={refresh}
              className="rounded border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
            >
              Обновить
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Chunks total" value={stats?.chunks_total ?? "—"} />
            <Stat label="Jobs (24h)" value={stats?.jobs_last_24h ?? "—"} />
            <Stat
              label="Failed"
              value={stats?.jobs_failed ?? "—"}
              tone={stats && stats.jobs_failed > 0 ? "warn" : "default"}
            />
            <Stat label="Queue depth" value={stats?.queue_depth ?? "—"} />
            <Stat label="p50 latency" value={stats ? `${stats.p50_duration_ms.toFixed(0)} ms` : "—"} />
            <Stat label="p95 latency" value={stats ? `${stats.p95_duration_ms.toFixed(0)} ms` : "—"} />
            <Stat
              label="Avg duration"
              value={stats ? `${stats.avg_duration_ms.toFixed(0)} ms` : "—"}
            />
            <Stat label="Embedding" value={embeddingBadge} />
          </div>
        </section>

        {/* === Last job / errors === */}
        {(lastJob || lastError) && (
          <section className="prism-card p-5">
            <h2 className="mb-3 text-lg font-medium text-slate-100">Результат</h2>
            {lastError && (
              <div className="rounded border border-red-700 bg-red-900/40 p-3 text-sm text-red-200">
                <strong>Ошибка:</strong> {lastError}
              </div>
            )}
            {lastJob && (
              <div className="rounded border border-slate-700 bg-slate-800/60 p-3 text-sm">
                <div>
                  <strong>Job ID:</strong> <span className="font-mono">{lastJob.job_id}</span>
                </div>
                <div>
                  <strong>Status:</strong>{" "}
                  <span
                    className={
                      lastJob.status === "done"
                        ? "text-emerald-400"
                        : lastJob.status === "failed"
                          ? "text-red-400"
                          : "text-sky-400"
                    }
                  >
                    {lastJob.status}
                  </span>
                </div>
                {lastJob.chunks_count > 0 && (
                  <div>
                    <strong>Chunks:</strong> {lastJob.chunks_count}
                  </div>
                )}
                {lastJob.duration_ms !== null && (
                  <div>
                    <strong>Duration:</strong> {lastJob.duration_ms} ms
                  </div>
                )}
                {lastJob.message && (
                  <div className="mt-1 text-slate-400">{lastJob.message}</div>
                )}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "warn";
}) {
  return (
    <div className="rounded border border-slate-700 bg-slate-800/60 p-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div
        className={
          tone === "warn"
            ? "mt-1 text-xl font-semibold text-amber-400"
            : "mt-1 text-xl font-semibold text-slate-100"
        }
      >
        {value}
      </div>
    </div>
  );
}
