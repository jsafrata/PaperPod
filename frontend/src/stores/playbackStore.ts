import { create } from "zustand";
import type { SpeakerRole } from "@/lib/types";

interface PlaybackState {
  currentTurnIndex: number;
  activeSpeaker: SpeakerRole | null;
  isPlaying: boolean;
  audioProgress: number;

  // Resume state (for after interruption)
  resumeTurnIndex: number | null;
  resumeTime: number | null;

  // Actions
  play: () => void;
  pause: () => void;
  setCurrentTurnIndex: (index: number) => void;
  setActiveSpeaker: (speaker: SpeakerRole | null) => void;
  setAudioProgress: (progress: number) => void;
  saveResumePoint: (turnIndex: number, time: number) => void;
  clearResumePoint: () => void;
  reset: () => void;
}

export const usePlaybackStore = create<PlaybackState>((set) => ({
  currentTurnIndex: 0,
  activeSpeaker: null,
  isPlaying: false,
  audioProgress: 0,
  resumeTurnIndex: null,
  resumeTime: null,

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  setCurrentTurnIndex: (index) => set({ currentTurnIndex: index }),
  setActiveSpeaker: (speaker) => set({ activeSpeaker: speaker }),
  setAudioProgress: (progress) => set({ audioProgress: progress }),
  saveResumePoint: (turnIndex, time) =>
    set({ resumeTurnIndex: turnIndex, resumeTime: time }),
  clearResumePoint: () => set({ resumeTurnIndex: null, resumeTime: null }),
  reset: () =>
    set({
      currentTurnIndex: 0,
      activeSpeaker: null,
      isPlaying: false,
      audioProgress: 0,
      resumeTurnIndex: null,
      resumeTime: null,
    }),
}));
