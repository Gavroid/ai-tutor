"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

const TOKEN_KEY = "ai-tutor-token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!r.ok) {
    const text = await r.text();
    let body: any = text;
    try {
      body = JSON.parse(text);
    } catch {}
    throw new ApiError(r.status, body);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export class ApiError extends Error {
  constructor(public status: number, public body: any) {
    super(typeof body === "string" ? body : JSON.stringify(body));
  }
}

import type { ChatMsg, MaterialDraftOut, MaterialListItem, Subject, TokenPair, Topic, User } from "@/types";

export const api = {
  // Auth
  register: (data: {
    email: string;
    password: string;
    display_name: string;
    role?: "student" | "parent" | "teacher" | "admin";
    grade?: number;
  }) => request<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<TokenPair>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request<User>("/api/v1/auth/me"),

  // Subjects & topics
  subjects: () => request<Subject[]>("/api/v1/subjects"),
  subjectTopics: (id: number) => request<Topic[]>(`/api/v1/subjects/${id}/topics`),
  topic: (id: number) => request<Topic>(`/api/v1/topics/${id}`),

  // AI
  aiPing: () => request<{ ok: boolean; model: string | null }>("/api/v1/ai/ping"),
  // Sprint 7.1 — AI-ответы теперь с content_html (server-rendered sanitized Markdown).
  // Sprint 4.1.3: sources для UI индикатора "📖 Источник".
  aiExplain: (topic_id: number) =>
    request<{
      content: string;
      content_html: string;
      model: string;
      sources: Array<{
        chunk_id?: number | null;
        material_id?: number | null;
        material_title: string;
        page_number?: number | null;
      }>;
    }>("/api/v1/ai/explain", { method: "POST", body: JSON.stringify({ topic_id }) }),
  aiChat: (history: ChatMsg[], topic_id?: number) =>
    request<{ content: string; content_html: string; model: string }>(
      "/api/v1/ai/chat",
      { method: "POST", body: JSON.stringify({ history, topic_id }) }
    ),
  aiGenerate: (topic_id: number, difficulty: number) =>
    request<{
      question_text: string;
      type: string;
      options: string[] | null;
      correct_answer: string;
      explanation: string;
      typical_mistakes: string[];
    }>("/api/v1/ai/generate-exercise", {
      method: "POST",
      body: JSON.stringify({ topic_id, difficulty }),
    }),
  aiCheck: (question_text: string, correct_answer: string, user_answer: string) =>
    request<{
      is_correct: boolean;
      score: number;
      first_error: string | null;
      explanation: string;
      hint_level: number;
      next_difficulty: number;
      // Sprint 4.3.1: error_type для context-aware hints (ARITHMETIC/CONCEPTUAL/LOGIC/CARELESS).
      error_type?: string | null;
    }>("/api/v1/ai/check-answer", {
      method: "POST",
      body: JSON.stringify({ question_text, correct_answer, user_answer }),
    }),
  // Sprint 4.3.2: hint теперь принимает error_type для context-aware подсказок.
  aiHint: (question_text: string, level: number, error_type?: string | null) =>
    request<{ content: string; content_html: string; model: string }>(
      "/api/v1/ai/hint",
      { method: "POST", body: JSON.stringify({ question_text, level, error_type: error_type ?? null }) }
    ),
  // Progress
  myProgress: () => request<{ topic_id: number; mastery_score: number; attempts_count: number; correct_count: number }[]>("/api/v1/progress"),
  myMistakes: () => request<{ id: number; topic_id: number; mistake_type: string; description: string; count: number }[]>("/api/v1/progress/mistakes"),
  recommendReview: () =>
    request<
      { topic_id: number; topic_name: string; subject_id: number; subject_name: string; mastery_score: number; attempts_count: number; correct_count: number }[]
    >("/api/v1/progress/recommend-review"),

  // Sprint 2.2 — Spaced Repetition
  dueForReview: (limit: number = 20) =>
    request<
      Array<{
        topic_id: number;
        topic_name: string;
        subject_name: string;
        mastery_score: number;
        review_count: number;
        next_review_at: string;
        days_overdue: number;
      }>
    >(`/api/v1/progress/due-for-review?limit=${limit}`),
  reviewResult: (data: {
    topic_id: number;
    quality: number;
    is_correct?: boolean;
    hint_used?: boolean;
  }) =>
    request<{
      topic_id: number;
      mastery_score: number;
      attempts_count: number;
      correct_count: number;
    }>("/api/v1/progress/review-result", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Sprint 2.1 — Student published materials
  studentMaterials: (params: { topic_id?: number; limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.topic_id !== undefined) search.set("topic_id", String(params.topic_id));
    if (params.limit) search.set("limit", String(params.limit));
    const qs = search.toString();
    return request<
      Array<{
        id: number;
        topic_id: number;
        title: string;
        content: string;
        source_type: string;
        published_at: string | null;
        created_at: string;
      }>
    >(`/api/v1/student/materials${qs ? "?" + qs : ""}`);
  },
  studentMaterial: (id: number) =>
    request<{
      id: number;
      topic_id: number;
      title: string;
      content: string;
      source_type: string;
      published_at: string | null;
      created_at: string;
    }>(`/api/v1/student/materials/${id}`),

  // Sprint 7.3 — автосохранение черновика урока.
  // Используется при T1D: прерывание в любой момент без потери прогресса.
  topicDraftLoad: async (topicId: number) => {
    try {
      const r = await request<{ topic_id: number; payload: Record<string, unknown>; updated_at: string }>(
        `/api/v1/student/topics/${topicId}/draft`
      );
      return { ok: true as const, payload: r.payload };
    } catch (e: unknown) {
      // 404 — нормальная ситуация (черновика нет)
      const err = e as { status?: number };
      if (err?.status === 404) return { ok: false as const };
      return { ok: false as const, error: err };
    }
  },
  topicDraftSave: (topicId: number, payload: Record<string, unknown>) =>
    request<{ topic_id: number; payload: Record<string, unknown>; updated_at: string }>(
      `/api/v1/student/topics/${topicId}/draft`,
      { method: "PUT", body: JSON.stringify({ payload }) }
    ),
  topicDraftClear: async (topicId: number) => {
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const r = await fetch(`${API_URL}/api/v1/student/topics/${topicId}/draft`, {
      method: "DELETE",
      headers,
    });
    if (!r.ok && r.status !== 204 && r.status !== 404) {
      throw new Error(`HTTP ${r.status}`);
    }
  },

  // Sprint 7.5 — баджи за усилие (НЕ за streak).
  studentBadges: () => {
    const token = getToken();
    if (!token) return Promise.resolve([]);
    return request<
      Array<{
        slug: string;
        title: string;
        description: string;
        icon: string;
        awarded_at: string | null;
        evidence: Record<string, unknown>;
      }>
    >("/api/v1/student/badges", {
      headers: { Authorization: `Bearer ${token}` },
    });
  },
  studentBadgesEvaluate: () => {
    const token = getToken();
    if (!token) return Promise.resolve([]);
    return request<string[]>("/api/v1/student/badges/evaluate", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  },

  // Sprint 2.3 — Voice transcription
  voiceTranscribe: async (audioBlob: Blob): Promise<{ text: string }> => {
    const form = new FormData();
    form.append("file", audioBlob, "recording.webm");
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const r = await fetch(`${API_URL}/api/v1/voice/transcribe`, {
      method: "POST",
      body: form,
      headers,
    });
    if (!r.ok) {
      const text = await r.text();
      let body: any = text;
      try { body = JSON.parse(text); } catch {}
      throw new ApiError(r.status, body);
    }
    return r.json();
  },
  // Stage 2 B.2: legacy `recordAttempt` (POST /api/v1/progress/attempts) was removed.
  // The frontend hot-path (`app/topics/[id]/page.tsx`) already uses the server-trusted
  // v2 endpoints below (`v2GenerateExercise`, `v2SubmitAnswer`). This helper was dead
  // code since Pilot Core Stage 1 and is unsafe (sends `correct_answer` from the client).
  // If any caller still needs progress tracking, they must migrate to v2.

  // Pilot Core Stage 1 — server-owned secure exercise flow.
  // Client НЕ получает correct_answer, отправляет только user_answer и
  // opaque exercise_id. Возвращаемый score/explanation — server-trusted.
  v2GenerateExercise: (data: { topic_id: number; difficulty?: number }) =>
    request<{
      exercise_id: number;
      question_text: string;
      type: string;
      options: string[] | null;
      difficulty: number;
      expires_at: string;
    }>("/api/v2/exercises/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  v2SubmitAnswer: (exercise_id: number, user_answer: string) =>
    request<{
      exercise_id: number;
      is_correct: boolean;
      score: number;
      feedback: string;
      explanation: string;
    }>(`/api/v2/exercises/${exercise_id}/answer`, {
      method: "POST",
      body: JSON.stringify({ user_answer }),
    }),
  // Diagnostics
  startDiagnostic: (subject_id: number) =>
    request<{ id: number; status: string }>("/api/v1/diagnostic/start", {
      method: "POST",
      body: JSON.stringify({ subject_id }),
    }),
  nextDiagnosticQuestion: (session_id: number) =>
    request<{
      session_id: number;
      topic_id: number;
      topic_name: string;
      subject_name: string;
      difficulty: number;
      question_text: string;
    }>(`/api/v1/diagnostic/${session_id}/next`),
  submitDiagnosticAnswer: (session_id: number, data: { topic_id: number; question_text: string; user_answer: string; correct_answer: string }) =>
    request<{ is_correct: boolean; answer_id: number }>(`/api/v1/diagnostic/${session_id}/answer`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  finishDiagnostic: (session_id: number) =>
    request<{
      id: number;
      total_questions: number;
      correct_count: number;
      overall_score: number;
      weak_topics: string | null;
      recommendations: string | null;
      status: string;
    }>(`/api/v1/diagnostic/${session_id}/finish`, { method: "POST" }),
  // Parents
  parentsInvite: () => request<{ code: string }>("/api/v1/parents/invite", { method: "POST" }),
  parentsChildren: () =>
    request<
      { student_id: number; display_name: string; email: string; linked_at: string }[]
    >("/api/v1/parents/children"),
  parentsOverview: (student_id: number) =>
    request<{
      student: { id: number; display_name: string; email: string };
      total_attempts: number;
      correct_attempts: number;
      accuracy: number;
      average_mastery: number;
      weak_topics: Array<{
        topic_id: number;
        topic_name: string;
        subject_name: string;
        mastery: number;
        attempts_count: number;
      }>;
      daily_activity: Array<{ date: string; attempts: number }>;
      privacy_note: string;
    }>(`/api/v1/parents/children/${student_id}`),
  linkParent: (code: string) =>
    request<{ ok: boolean }>("/api/v1/students/link-parent", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  // Sprint 3.2 — Parent dashboard
  parentDashboard: (studentId: number) =>
    request<{
      student: { id: number; display_name: string; email: string };
      generated_at: string;
      total_attempts: number;
      correct_attempts: number;
      accuracy: number;
      average_mastery: number;
      subject_mastery: Array<{
        subject_id: number;
        subject_name: string;
        topics_total: number;
        topics_attempted: number;
        avg_mastery: number;
        accuracy: number;
      }>;
      weak_topics: Array<{
        topic_id: number;
        topic_name: string;
        subject_name: string;
        mastery: number;
        attempts_count: number;
      }>;
      top_mistakes: Array<{
        mistake_type: string;
        description: string;
        topic_id: number;
        topic_name: string;
        count: number;
        last_seen: string;
      }>;
      streak: {
        current_streak_days: number;
        longest_streak_days: number;
        last_active_date: string | null;
        total_active_days: number;
      };
      time_stats: {
        total_attempts: number;
        last_7_days: number;
        last_30_days: number;
        avg_per_active_day: number;
      };
      daily_activity_30d: Array<{ date: string; attempts: number }>;
      due_for_review_count: number;
      privacy_note: string;
    }>(`/api/v1/parents/students/${studentId}/dashboard`),
  passwordResetRequest: (email: string) =>
    request<{ ok: boolean; message: string }>("/api/v1/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  passwordResetConfirm: (token: string, new_password: string) =>
    request<{ ok: boolean; message: string }>("/api/v1/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),
  refreshToken: (refresh_token: string) =>
    request<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }>(
      "/api/v1/auth/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token }) }
    ),
  // Admin
  adminStats: () =>
    request<{
      total_users: number;
      active_users: number;
      by_role: { student: number; parent: number; teacher: number; admin: number };
    }>("/api/v1/admin/stats"),
  adminUsers: () =>
    request<
      Array<{
        id: number;
        email: string;
        display_name: string;
        role: string;
        is_active: boolean;
        created_at: string;
      }>
    >("/api/v1/admin/users"),
  adminAuditLog: (params: { user_id?: number; action?: string; since?: string; until?: string; limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.user_id !== undefined) search.set("user_id", String(params.user_id));
    if (params.action) search.set("action", params.action);
    if (params.since) search.set("since", params.since);
    if (params.until) search.set("until", params.until);
    if (params.limit) search.set("limit", String(params.limit));
    const qs = search.toString();
    return request<
      Array<{
        id: number;
        user_id: number | null;
        action: string;
        entity: string | null;
        entity_id: string | null;
        details: string | null;
        ip_address: string | null;
        created_at: string;
      }>
    >(`/api/v1/admin/audit-log${qs ? "?" + qs : ""}`);
  },
  adminDeactivateUser: (user_id: number) =>
    request<{ ok: boolean }>(`/api/v1/admin/users/${user_id}/deactivate`, { method: "POST" }),
  adminTestNotification: (email: string) =>
    request<{
      ok: boolean;
      status: string;
      error: string | null;
      smtp_configured: boolean;
      record_id: number;
    }>(`/api/v1/admin/notifications/test?email=${encodeURIComponent(email)}`, {
      method: "POST",
    }),
  adminExpireStaleDiagnostics: (ttl_hours: number = 24) =>
    request<{ ok: boolean; expired_count: number }>(
      `/api/v1/admin/diagnostics/expire-stale?ttl_hours=${ttl_hours}`,
      { method: "POST" }
    ),

  // Sprint 3.6.3: AI Kill Switch
  adminGetAiKillSwitch: () =>
    request<{ user_ids: number[]; raw: string }>(
      `/api/v1/admin/ai-kill-switch`,
      { method: "GET" }
    ),
  adminAddAiKillSwitch: (user_id: number) =>
    request<{ ok: boolean; user_id: number; all_killed?: number[]; already_killed?: boolean }>(
      `/api/v1/admin/ai-kill-switch/${user_id}`,
      { method: "POST" }
    ),
  adminRemoveAiKillSwitch: (user_id: number) =>
    request<{ ok: boolean; user_id: number; all_killed?: number[]; not_killed?: boolean }>(
      `/api/v1/admin/ai-kill-switch/${user_id}`,
      { method: "DELETE" }
    ),

  // Teacher (Sprint 1.2-1.3)
  teacherListMaterials: (params: { status?: string; topic_id?: number; limit?: number; offset?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.status) search.set("status", params.status);
    if (params.topic_id !== undefined) search.set("topic_id", String(params.topic_id));
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    const qs = search.toString();
    return request<MaterialListItem[]>(`/api/v1/teacher/materials${qs ? "?" + qs : ""}`);
  },
  teacherGetMaterial: (id: number) =>
    request<MaterialDraftOut>(`/api/v1/teacher/materials/${id}`),
  teacherGenerateMaterial: (data: {
    topic_id: number;
    source_type: "text" | "file" | "topic";
    text?: string;
    file_path?: string;
    topic_hint?: string;
  }) =>
    request<MaterialDraftOut>("/api/v1/teacher/materials/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  teacherUploadSource: async (file: File): Promise<{ file_path: string; size: number; filename: string }> => {
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const r = await fetch(`${API_URL}/api/v1/teacher/materials/upload-source`, {
      method: "POST",
      body: form,
      headers,
    });
    if (!r.ok) {
      const text = await r.text();
      let body: any = text;
      try { body = JSON.parse(text); } catch {}
      throw new ApiError(r.status, body);
    }
    return r.json();
  },
  teacherApprove: (id: number) =>
    request<MaterialDraftOut>(`/api/v1/teacher/materials/${id}/approve`, { method: "POST" }),
  teacherPublish: (id: number) =>
    request<MaterialDraftOut>(`/api/v1/teacher/materials/${id}/publish`, { method: "POST" }),
  teacherUnpublish: (id: number) =>
    request<MaterialDraftOut>(`/api/v1/teacher/materials/${id}/unpublish`, { method: "POST" }),
  teacherUpdateMaterial: (id: number, data: { title?: string; content?: MaterialDraftOut["content"] }) =>
    request<MaterialDraftOut>(`/api/v1/teacher/materials/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  teacherDeleteMaterial: (id: number) =>
    request<{ ok: boolean }>(`/api/v1/teacher/materials/${id}`, { method: "DELETE" }),
};