export type User = {
  id: number;
  email: string;
  display_name: string;
  role: "student" | "parent" | "teacher" | "admin";
  is_active: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
};

export type Subject = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  color: string | null;
  icon: string | null;
  recommended_grade: number;
  age_min: number;
  age_max: number;
  is_active: boolean;
  mvp_status?: "mvp_ready" | "preview" | string;
  support_note?: string;
  rag_ready?: boolean;
  practice_ready?: boolean;
};

// === Teacher (Sprint 1.2-1.3) ===
export type MaterialStatus = "draft" | "ai_generated" | "teacher_approved" | "published";
export type SourceType = "text" | "file" | "topic";
export type Difficulty = "easy" | "medium" | "hard";

export type KeyIdea = { idea: string; terms: string[] };
export type PracticeTask = {
  difficulty: Difficulty;
  question_text: string;
  reference_solution: string;
  typical_mistakes: string[];
  hint: string | null;
};
export type TestQuestion = {
  question_text: string;
  options: string[];
  correct_index: number;
  explanation: string;
};
export type Flashcard = { question: string; answer: string };

export type MaterialContent = {
  title: string;
  purpose: string;
  connection_to_prior: string | null;
  key_ideas: KeyIdea[];
  rule_or_formula: string | null;
  simple_example: string | null;
  schema_or_table: string | null;
  misconception: string | null;
  common_mistake: string | null;
  self_check_questions: string[];
  practice_tasks: PracticeTask[];
  mini_test: TestQuestion[];
  flashcards: Flashcard[];
  ai_uncertainty_notes: string[];
};

export type MaterialListItem = {
  id: number;
  topic_id: number;
  title: string;
  status: MaterialStatus;
  source_type: SourceType;
  generated_by: number | null;
  approved_by: number | null;
  published_at: string | null;
  created_at: string;
};

export type MaterialDraftOut = {
  id: number;
  topic_id: number;
  title: string;
  content: MaterialContent;
  status: MaterialStatus;
  source_type: SourceType;
  generated_by: number | null;
  approved_by: number | null;
  published_at: string | null;
  created_at: string;
};

export type Topic = {
  id: number;
  section_id: number;
  name: string;
  description: string | null;
  difficulty: number;
  order_index: number;
};

export type TopicFollowup = {
  label: string;
  prompt: string;
  kind: "choice" | "next" | string;
  order_index: number;
};

export type TopicPracticeFallback = {
  question_text: string;
  type: string;
  options: string[] | null;
  correct_answer: string;
  explanation: string;
  typical_mistakes: string[];
  difficulty: number;
  order_index: number;
  is_active: boolean;
};

export type TopicStatusUpdate = {
  explain_status?: string;
  practice_status?: string;
  source_status?: string;
  manual_qa_status?: string;
  notes?: string;
};

export type RagRebuildJob = {
  job_id: string;
  topic_id: number | null;
  subject_id: number | null;
  status: string;
  chunks_before: number;
  chunks_after: number | null;
  message: string;
};

export type TopicReadiness = {
  topic_id: number;
  topic_name: string;
  section_id: number;
  section_name: string;
  subject_id: number;
  subject_name: string;
  priority: "P0" | "P1" | "P2" | string;
  material_count: number;
  chunk_count: number;
  fallback_count: number;
  followup_count: number;
  explain_status: string;
  practice_status: string;
  source_status: string;
  manual_qa_status: string;
};

export type ChatMsg = {
  role: "user" | "assistant";
  content: string;
  // Sprint 4.1.3: RAG-источники для UI индикатора "📖 Источник".
  sources?: Array<{
    chunk_id?: number | string | null;
    material_id?: number | null;
    material_title: string;
    page_number?: number | null;
    part?: number | null;
    topic_id?: number | null;
    topic_name?: string | null;
    snippet?: string | null;
    label?: string | null;
    citation_confidence?: "verified" | string;
  }>;
  // Sprint 12: error info если AI вызов упал.
  // UI показывает вкладку «Подробности» с error-сообщением.
  error?: string;
};

export type MathTopicPlan = {
  topic_id: number;
  order: number;
  section: string;
  tier: "base" | "medium" | "hard" | string;
  focus: string;
  checkpoint: boolean;
  next_topic_id: number | null;
};
