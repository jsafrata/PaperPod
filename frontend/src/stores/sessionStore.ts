import { create } from "zustand";
import type { SessionMode, Turn, Visual } from "@/lib/types";

interface TranscriptEntry {
  speaker: string;
  text: string;
  isUser?: boolean;
}

interface RestyleProgress {
  total: number;
  done: number;
}

interface SessionState {
  sessionId: string | null;
  paperId: string | null;
  mode: SessionMode;
  turns: Turn[];
  transcript: TranscriptEntry[];
  currentSection: string;
  activeVisual: Visual | null;
  weakConcepts: string[];
  activeRestyle: string | null;
  restyleProgress: RestyleProgress | null;

  // Actions
  setSession: (sessionId: string, paperId: string) => void;
  setMode: (mode: SessionMode) => void;
  setTurns: (turns: Turn[]) => void;
  updateTurn: (index: number, turn: Turn) => void;
  appendTranscript: (entry: TranscriptEntry) => void;
  updateLastUserTranscript: (text: string) => void;
  updateLastTranscriptText: (text: string) => void;
  setCurrentSection: (section: string) => void;
  setActiveVisual: (visual: Visual | null) => void;
  addWeakConcept: (concept: string) => void;
  setActiveRestyle: (directive: string | null) => void;
  setRestyleProgress: (progress: RestyleProgress | null) => void;
  incrementRestyleProgress: () => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  paperId: null,
  mode: "processing",
  turns: [],
  transcript: [],
  currentSection: "intro",
  activeVisual: null,
  weakConcepts: [],
  activeRestyle: null,
  restyleProgress: null,

  setSession: (sessionId, paperId) => set({ sessionId, paperId }),
  setMode: (mode) => set({ mode }),
  setTurns: (turns) => set({ turns }),
  updateTurn: (index, turn) =>
    set((state) => {
      const newTurns = [...state.turns];
      if (index >= 0 && index < newTurns.length) {
        newTurns[index] = turn;
      }
      return { turns: newTurns };
    }),
  appendTranscript: (entry) =>
    set((state) => ({ transcript: [...state.transcript, entry] })),
  updateLastUserTranscript: (text) =>
    set((state) => {
      const transcript = [...state.transcript];
      // Find the last user entry and update its text
      for (let i = transcript.length - 1; i >= 0; i--) {
        if (transcript[i].isUser) {
          transcript[i] = { ...transcript[i], text };
          break;
        }
      }
      return { transcript };
    }),
  updateLastTranscriptText: (text) =>
    set((state) => {
      if (state.transcript.length === 0) return state;
      const transcript = [...state.transcript];
      transcript[transcript.length - 1] = { ...transcript[transcript.length - 1], text };
      return { transcript };
    }),
  setCurrentSection: (section) => set({ currentSection: section }),
  setActiveVisual: (visual) => set({ activeVisual: visual }),
  addWeakConcept: (concept) =>
    set((state) => ({
      weakConcepts: state.weakConcepts.includes(concept)
        ? state.weakConcepts
        : [...state.weakConcepts, concept],
    })),
  setActiveRestyle: (directive) => set({ activeRestyle: directive }),
  setRestyleProgress: (progress) => set({ restyleProgress: progress }),
  incrementRestyleProgress: () =>
    set((state) => ({
      restyleProgress: state.restyleProgress
        ? { ...state.restyleProgress, done: state.restyleProgress.done + 1 }
        : null,
    })),
  reset: () =>
    set({
      sessionId: null,
      paperId: null,
      mode: "processing",
      turns: [],
      transcript: [],
      currentSection: "intro",
      activeVisual: null,
      weakConcepts: [],
      activeRestyle: null,
      restyleProgress: null,
    }),
}));
