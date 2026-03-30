"use client";

import { useRef, useCallback, useEffect } from "react";
import { usePlaybackStore } from "@/stores/playbackStore";
import { useSessionStore } from "@/stores/sessionStore";
import type { Turn, SpeakerRole } from "@/lib/types";

export function useAudioPlayer(turns: Turn[]) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const nextAudioRef = useRef<HTMLAudioElement | null>(null);
  const autoAdvanceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // When true, handleEnded will pause instead of advancing to next turn
  const blockAdvanceRef = useRef(false);
  // Called when handleEnded blocks (turn ended while blockAdvance is true)
  const onBlockedRef = useRef<(() => void) | null>(null);

  const {
    currentTurnIndex,
    isPlaying,
    setCurrentTurnIndex,
    setActiveSpeaker,
    setAudioProgress,
    play: storePlay,
    pause: storePause,
    saveResumePoint,
    resumeTurnIndex,
    resumeTime,
    clearResumePoint,
  } = usePlaybackStore();

  const { appendTranscript, setCurrentSection } = useSessionStore();

  const currentTurn = turns[currentTurnIndex] || null;

  // Keep turns and currentTurnIndex in refs so callbacks always see latest
  const turnsRef = useRef(turns);
  turnsRef.current = turns;
  const currentTurnIndexRef = useRef(currentTurnIndex);
  currentTurnIndexRef.current = currentTurnIndex;

  // Initialize audio element
  useEffect(() => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
    }
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
      if (autoAdvanceTimerRef.current) {
        clearTimeout(autoAdvanceTimerRef.current);
      }
    };
  }, []);

  const clearAutoAdvance = useCallback(() => {
    if (autoAdvanceTimerRef.current) {
      clearTimeout(autoAdvanceTimerRef.current);
      autoAdvanceTimerRef.current = null;
    }
  }, []);

  // Load and play a specific turn
  const loadTurn = useCallback(
    (index: number) => {
      const turn = turnsRef.current[index];
      if (!turn || !audioRef.current) return;

      clearAutoAdvance();

      setCurrentTurnIndex(index);
      setActiveSpeaker(turn.speaker as SpeakerRole);
      setCurrentSection(turn.section);

      // Add to transcript
      appendTranscript({ speaker: turn.speaker, text: turn.text });

      if (turn.audio_url) {
        audioRef.current.src = turn.audio_url;
        audioRef.current.load();
      } else {
        // No audio — clear any current audio src so we don't replay old audio
        audioRef.current.pause();
        audioRef.current.src = "";
      }

      // Prefetch next turn
      const nextTurn = turnsRef.current[index + 1];
      if (nextTurn?.audio_url) {
        nextAudioRef.current = new Audio(nextTurn.audio_url);
      } else {
        nextAudioRef.current = null;
      }
    },
    [setCurrentTurnIndex, setActiveSpeaker, setCurrentSection, appendTranscript, clearAutoAdvance]
  );

  // Auto-advance for text-only turns — use a ref-based function to allow recursion
  const loadTurnRef = useRef(loadTurn);
  loadTurnRef.current = loadTurn;

  const scheduleAutoAdvance = useCallback(
    (fromIndex: number) => {
      clearAutoAdvance();
      const t = turnsRef.current[fromIndex];
      const wordCount = t?.text?.split(/\s+/).length || 20;
      const delay = Math.min(Math.max(wordCount * 150, 2000), 6000);

      autoAdvanceTimerRef.current = setTimeout(() => {
        autoAdvanceTimerRef.current = null;
        const nextIndex = fromIndex + 1;
        if (nextIndex < turnsRef.current.length) {
          loadTurnRef.current(nextIndex);
          const nextTurn = turnsRef.current[nextIndex];
          if (nextTurn?.audio_url && audioRef.current) {
            audioRef.current.play().catch(() => {});
          } else {
            // Recurse via setTimeout — no useCallback circular dep
            scheduleAutoAdvance(nextIndex);
          }
        } else {
          storePause();
          setActiveSpeaker(null);
        }
      }, delay);
    },
    [clearAutoAdvance, storePause, setActiveSpeaker]
  );

  // Handle turn end — advance to next
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => {
      // If advance is blocked (restyle pending), pause and notify once
      if (blockAdvanceRef.current) {
        storePause();
        const cb = onBlockedRef.current;
        onBlockedRef.current = null;  // Clear so it doesn't fire again
        cb?.();
        return;
      }

      // Use ref to get actual current index (not stale closure)
      const nextIndex = currentTurnIndexRef.current + 1;
      if (nextIndex < turnsRef.current.length) {
        const nextTurn = turnsRef.current[nextIndex];
        if (
          nextAudioRef.current &&
          nextTurn?.audio_url &&
          nextAudioRef.current.src !== nextTurn.audio_url
        ) {
          nextAudioRef.current = null;
        }
        loadTurnRef.current(nextIndex);
        if (nextTurn?.audio_url) {
          // Play when audio data is loaded
          const onLoaded = () => {
            audio.removeEventListener("loadeddata", onLoaded);
            audio.play().catch(() => {});
          };
          audio.addEventListener("loadeddata", onLoaded);
        } else {
          scheduleAutoAdvance(nextIndex);
        }
      } else {
        // Podcast finished
        storePause();
        setActiveSpeaker(null);
      }
    };

    const handleTimeUpdate = () => {
      if (audio.duration > 0) {
        setAudioProgress(audio.currentTime / audio.duration);
      }
    };

    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    return () => {
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
    };
  }, [setAudioProgress, storePause, setActiveSpeaker, scheduleAutoAdvance]);

  // Play
  const play = useCallback(() => {
    if (!audioRef.current) return;

    // If no turn loaded yet, start from beginning
    if (!audioRef.current.src || audioRef.current.src === window.location.href) {
      if (turnsRef.current.length > 0) {
        loadTurn(0);
      }
    }

    const turn = turnsRef.current[currentTurnIndex] || turnsRef.current[0];
    if (turn?.audio_url) {
      audioRef.current.play().catch((e) => {
        console.warn("Audio play failed:", e);
        scheduleAutoAdvance(currentTurnIndex);
      });
    } else {
      scheduleAutoAdvance(currentTurnIndex);
    }
    storePlay();
  }, [currentTurnIndex, loadTurn, storePlay, scheduleAutoAdvance]);

  // Pause
  const pause = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    clearAutoAdvance();
    storePause();
  }, [storePause, clearAutoAdvance]);

  // Toggle
  const toggle = useCallback(() => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  }, [isPlaying, play, pause]);

  // Interrupt — pause and save resume point
  const interrupt = useCallback(() => {
    if (audioRef.current) {
      saveResumePoint(currentTurnIndex, audioRef.current.currentTime);
      audioRef.current.pause();
    }
    clearAutoAdvance();
    storePause();
  }, [currentTurnIndex, saveResumePoint, storePause, clearAutoAdvance]);

  // Resume from saved point
  const resume = useCallback(() => {
    if (audioRef.current && resumeTurnIndex !== null) {
      if (resumeTurnIndex !== currentTurnIndex) {
        loadTurn(resumeTurnIndex);
      }
      if (resumeTime !== null) {
        audioRef.current.currentTime = resumeTime;
      }
      audioRef.current.play().catch(() => {});
      storePlay();
      clearResumePoint();
    }
  }, [resumeTurnIndex, resumeTime, currentTurnIndex, loadTurn, storePlay, clearResumePoint]);

  // Play an injected turn (e.g. from Q&A response) then resume
  const playInjectedAudio = useCallback(
    async (audioUrl: string, onComplete?: () => void) => {
      if (!audioRef.current) return;

      const injectedAudio = new Audio(audioUrl);
      injectedAudio.addEventListener("ended", () => {
        onComplete?.();
      });
      await injectedAudio.play().catch(() => {});
    },
    []
  );

  // Seek to specific turn
  const seekToTurn = useCallback(
    (index: number) => {
      if (index >= 0 && index < turnsRef.current.length) {
        loadTurn(index);
        if (isPlaying && audioRef.current) {
          audioRef.current.play().catch(() => {});
        }
      }
    },
    [loadTurn, isPlaying]
  );

  // Skip directly to a turn and play — bypasses resume points entirely.
  // Uses refs to avoid stale closure issues.
  const skipToTurn = useCallback(
    (index: number) => {
      clearAutoAdvance();
      const turn = turnsRef.current[index];
      if (!turn || !audioRef.current) return;
      clearResumePoint();
      audioRef.current.pause();
      // Load the new turn
      loadTurnRef.current(index);
      if (turn.audio_url) {
        const audio = audioRef.current;
        const onLoaded = () => {
          audio.removeEventListener("loadeddata", onLoaded);
          audio.play().catch(() => {});
        };
        audio.addEventListener("loadeddata", onLoaded);
      } else {
        scheduleAutoAdvance(index);
      }
      storePlay();
    },
    [clearAutoAdvance, clearResumePoint, storePlay, scheduleAutoAdvance]
  );

  // Block/unblock auto-advance (for restyle waiting)
  const setBlockAdvance = useCallback((block: boolean, onBlocked?: () => void) => {
    blockAdvanceRef.current = block;
    onBlockedRef.current = onBlocked || null;
  }, []);

  const setPlaybackRate = useCallback((rate: number) => {
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  }, []);

  return {
    play,
    pause,
    toggle,
    interrupt,
    resume,
    seekToTurn,
    skipToTurn,
    setBlockAdvance,
    setPlaybackRate,
    playInjectedAudio,
    currentTurn,
    isPlaying,
    currentTurnIndex,
  };
}
