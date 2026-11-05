export type Role = "student" | "officer" | "admin";

export interface College {
  id: string;
  name: string;
  code: string;
  city: string | null;
  placement_date: string | null;
  is_active: boolean;
  created_at: string;
  student_count: number;
}

export interface User {
  id: string;
  college_id: string;
  college_name: string | null;
  email: string;
  name: string;
  role: Role;
  branch: string | null;
  target_role: string | null;
  avatar_url: string | null;
  xp: number;
  streak_count: number;
  consent_share_analytics: boolean;
  onboarding_complete: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ResumeProject {
  name?: string;
  description?: string;
  tech?: string[];
  bullets?: string[];
}

export interface ParsedResume {
  full_name?: string;
  email?: string;
  phone?: string;
  links?: string[];
  summary?: string;
  skills?: string[];
  projects?: ResumeProject[];
  experience?: Array<{
    company?: string;
    title?: string;
    bullets?: string[];
  }>;
}

export interface Resume {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: "parsed" | "needs_review" | "failed";
  used_ocr: boolean;
  pages: number;
  warnings: string[];
  created_at: string;
  raw_text?: string;
  parsed_data?: ParsedResume;
}

export interface Suggestion {
  id: string;
  target_section: string;
  category: string;
  original: string;
  improved: string;
  rationale: string;
  supported: boolean;
  decision: "pending" | "accepted" | "rejected";
}

export interface MissingEvidence {
  item: string;
  reason: string;
}

export interface Analysis {
  id: string;
  resume_id: string;
  target_role: string;
  job_description: string;
  score: number;
  subscores: Record<string, number>;
  suggestions: Suggestion[];
  missing_evidence: MissingEvidence[];
  injection_flags: string[];
  prompt_version: string;
  model: string;
  created_at: string;
}

export interface RubricCriterion {
  key: string;
  label: string;
  weight: number;
  description: string;
}

export interface Rubric {
  version: string;
  label: string;
  criteria: RubricCriterion[];
}

export interface Interview {
  id: string;
  resume_id: string | null;
  role: string;
  status: "active" | "completed" | "abandoned";
  current_round: "project" | "technical" | "hr";
  rubric_version: string;
  prompt_version: string;
  model: string;
  overall_score: number | null;
  duration_seconds: number;
  hint_count: number;
  variance_flag: boolean;
  needs_review: boolean;
  started_at: string;
  completed_at: string | null;
}

export interface InterviewTurn {
  id: string;
  idx: number;
  round: "project" | "technical" | "hr";
  speaker: "interviewer" | "candidate" | "system";
  content: string;
  is_followup: boolean;
  hint_used: boolean;
  created_at: string;
}

export interface InterviewDetail extends Interview {
  rubric_scores: Array<{
    key: string;
    label: string;
    weight: number;
    score: number;
    note: string;
    improvement: string;
  }>;
  feedback: FeedbackSummary & { needs_review?: boolean; spread?: number; samples_used?: number };
  turns: InterviewTurn[];
}

export interface FeedbackSummary {
  summary?: string;
  strengths?: string[];
  improvements?: string[];
  samples_used?: number;
  spread?: number;
  needs_review?: boolean;
  rubric_label?: string;
}

export interface ScoreCriterion {
  key: string;
  label: string;
  weight: number;
  score: number;
  note: string;
  improvement: string;
}

export interface Feedback {
  interview_id: string;
  overall_score: number | null;
  rubric_version: string;
  criteria: ScoreCriterion[];
  feedback: FeedbackSummary;
  transcript: InterviewTurn[];
  variance_flag: boolean;
}

export interface RadarPoint {
  key: string;
  label: string;
  value: number;
}

export interface Badge {
  key: string;
  label: string;
  description: string;
  earned: boolean;
  icon: string;
}

export interface NextAction {
  title: string;
  description: string;
  href: string;
  cta: string;
  kind: string;
}

export interface HistoryItem {
  id: string;
  kind: string;
  title: string;
  subtitle: string;
  score: number | null;
  created_at: string;
}

export interface Dashboard {
  readiness: number;
  readiness_delta: number;
  band: string;
  has_resume: boolean;
  has_interview: boolean;
  radar: RadarPoint[];
  streak: number;
  xp: number;
  level: number;
  level_progress: number;
  badges: Badge[];
  next_action: NextAction;
  history: HistoryItem[];
  placement_date: string | null;
  days_to_placement: number | null;
  resume_score: number | null;
  interview_score: number | null;
  completed_interviews: number;
  total_interviews: number;
  skill_gaps: string[];
}

export interface Usage {
  month: string;
  tokens: number;
  cost_usd: number;
  budget_usd: number;
  remaining_usd: number;
  percent_used: number;
}

export interface HeatmapCell {
  branch: string;
  criterion: string;
  value: number;
  students: number;
}

export interface OfficerOverview {
  kpis: {
    total_students: number;
    active_30d: number;
    resume_uploads: number;
    interviews_completed: number;
    avg_readiness: number;
    placement_date: string | null;
    days_to_placement: number | null;
  };
  heatmap: HeatmapCell[];
  criteria: string[];
  branches: string[];
  funnel: Array<{ stage: string; count: number; percent: number }>;
  weakest_skills: Array<{ skill: string; gap: number; students_affected: number }>;
  cohort_progress: Array<{ week: string; interviews: number; avg_score: number }>;
  batch_comparison: Array<{
    branch: string;
    students: number;
    readiness: number;
    interviews: number;
    resumes: number;
  }>;
  students: Array<{
    id: string;
    display_name: string;
    branch: string | null;
    readiness: number | null;
    interviews: number;
    last_active: string | null;
    consent: boolean;
  }>;
  generated_at: string;
  aggregate_only: boolean;
}

export interface Question {
  id: string;
  college_id: string | null;
  prompt: string;
  ideal_answer: string;
  role: string;
  topic: string;
  difficulty: string;
  key_points: string[];
  is_active: boolean;
  created_at: string;
}

export interface RubricVersion {
  id: string;
  version: string;
  label: string;
  criteria: Array<{ key: string; label: string; weight: number; description: string }>;
  is_active: boolean;
  created_at: string;
}

export interface AdminOverview {
  colleges: number;
  students: number;
  interviews: number;
  usage: Array<{
    college_id: string;
    college_name: string;
    month: string;
    tokens: number;
    cost_usd: number;
    users_billable: number;
  }>;
}

export interface WSEvent {
  type: string;
  [key: string]: unknown;
}
