// --- Speaker ---

export type SpeakerRole = "host" | "expert" | "skeptic";

export type SessionMode =
  | "processing"
  | "playing"
  | "paused"
  | "interrupted"
  | "quiz"
  | "recap";

// --- Turn ---

export interface Turn {
  index: number;
  speaker: SpeakerRole;
  text: string;
  audio_url: string | null;
  visual_id: string | null;
  section: string;
}

// --- Visual ---

export interface Visual {
  id: string;
  type: "figure" | "table" | "ai_generated";
  image_url: string;
  caption: string | null;
  page_number: number | null;
  provenance: "from_paper" | "ai_generated";
}

// --- Session ---

export interface SessionData {
  session_id: string;
  paper_id: string;
  mode: SessionMode;
  difficulty: string;
  paper_title: string;
  current_turn_index: number;
  total_turns: number;
}

// --- Processing ---

export interface ProcessingStep {
  name: string;
  status: "pending" | "running" | "done";
}

export interface PaperStatus {
  paper_id: string;
  status: string;
  title: string;
  steps: ProcessingStep[];
  session_id?: string;
  summary?: string;
}

// --- Quiz ---

export interface QuizQuestion {
  question_id: string;
  text: string;
  section: string;
}

export interface QuizResult {
  correct: boolean;
  feedback: string;
  weak_concepts: string[];
}

// --- Recap ---

export interface Flashcard {
  front: string;
  back: string;
}

export interface RecapData {
  takeaways: string[];
  limitations: string[];
  flashcards: Flashcard[];
  weak_concepts: string[];
}

// --- WebSocket Messages ---

export type WSClientMessage =
  | { type: "interrupt"; question: string; current_turn_index: number; use_live?: boolean }
  | { type: "voice_interrupt"; audio: string; current_turn_index: number; sample_rate?: number }
  | { type: "quiz_start"; section?: string; current_turn_index?: number }
  | { type: "quiz_answer"; question_id: string; answer: string }
  | { type: "simplify"; current_turn_index: number; use_live?: boolean }
  | { type: "go_deeper"; current_turn_index: number; use_live?: boolean };

export type WSServerMessage =
  // Non-streaming (TTS fallback)
  | { type: "answer"; speaker: string; text: string; audio_url: string | null; visual: Visual | null }
  | { type: "resume"; from_turn: number; host_bridge_text?: string; host_bridge_audio?: string }
  // Streaming (Live API)
  | { type: "audio_chunk"; data: string; mime_type: string }
  | { type: "transcript_delta"; text: string; full_text: string }
  | { type: "answer_complete"; speaker: string; text: string }
  | { type: "resume_audio_chunk"; data: string; mime_type: string }
  | { type: "resume_transcript_delta"; text: string }
  | { type: "resume_from_turn"; turn_index: number }
  | { type: "resume_complete" }
  // Quiz
  | { type: "quiz_question"; question_id: string; text: string; speaker: string; audio_url: string | null }
  | { type: "quiz_feedback"; correct: boolean; explanation: string; speaker: string; audio_url: string | null; weak_concepts: string[] }
  // Voice transcription
  | { type: "user_transcript"; text: string }
  // Restyle (background regeneration)
  | { type: "restyle_started"; directive: string; from_turn_index: number }
  | { type: "turn_update"; index: number; speaker: string; text: string; audio_url: string | null; visual_id: string | null; section: string }
  | { type: "restyle_complete" }
  // Other
  | { type: "visual_update"; visual_id: string; url: string; caption: string; provenance: string }
  | { type: "error"; message: string };
