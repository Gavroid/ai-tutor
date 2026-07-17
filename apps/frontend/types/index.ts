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

export type ChatMsg = {
  role: "user" | "assistant";
  content: string;
  // Sprint 4.1.3: RAG-источники для UI индикатора "📖 Источник".
  sources?: Array<{
    chunk_id?: number | null;
    material_id?: number | null;
    material_title: string;
    page_number?: number | null;
  }>;
};