"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { getPodcastTurns, getSession, getVisuals, resolveUrl } from "@/lib/api";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useStreamingAudio } from "@/hooks/useStreamingAudio";
import { useMicrophone } from "@/hooks/useMicrophone";
import { usePlaybackStore } from "@/stores/playbackStore";
import { useSessionStore } from "@/stores/sessionStore";
import { SpeakerPanel } from "@/components/listening/SpeakerPanel";
import { TranscriptPanel } from "@/components/listening/TranscriptPanel";
import { VisualPanel } from "@/components/listening/VisualPanel";
import { SectionProgress } from "@/components/listening/SectionProgress";
import { ControlBar } from "@/components/listening/ControlBar";
import { QuizOverlay } from "@/components/quiz/QuizOverlay";
import { toast } from "sonner";
import type { WSServerMessage } from "@/lib/types";

export default function ListeningPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;
  const [isWaiting, setIsWaiting] = useState(false);
  const [quizOpen, setQuizOpen] = useState(false);
  const [quizQuestion, setQuizQuestion] = useState<{ question_id: string; text: string } | null>(null);
  const [quizFeedback, setQuizFeedback] = useState<{ correct: boolean; explanation: string; weak_concepts: string[] } | null>(null);
  const [quizWaiting, setQuizWaiting] = useState(false);
  const [streamingTranscript, setStreamingTranscript] = useState("");
  const resumeFromTurnRef = useRef<number | null>(null);
  const restyleConfirmedRef = useRef(false);
  const restylePendingRef = useRef(false);
  const isRestyleResponseRef = useRef(false);
  const streamingEntryAddedRef = useRef(false);
  const [isRestyleWaiting, setIsRestyleWaiting] = useState(false);
  const waitingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Safety timeout: if stuck in "waiting" for 30s, auto-clear and resume
  useEffect(() => {
    if (isWaiting) {
      waitingTimeoutRef.current = setTimeout(() => {
        console.warn("Waiting timeout — clearing stuck state");
        setIsWaiting(false);
        // Skip to next turn, don't replay interrupted one
        skipToTurn(usePlaybackStore.getState().currentTurnIndex + 1);
      }, 30000);
    } else {
      if (waitingTimeoutRef.current) {
        clearTimeout(waitingTimeoutRef.current);
        waitingTimeoutRef.current = null;
      }
    }
    return () => {
      if (waitingTimeoutRef.current) clearTimeout(waitingTimeoutRef.current);
    };
  }, [isWaiting]);

  const { activeSpeaker, currentTurnIndex, setActiveSpeaker, clearResumePoint } = usePlaybackStore();
  const {
    transcript, currentSection, activeVisual,
    setSession, setTurns, setMode, appendTranscript, updateLastUserTranscript,
    updateTurn, updateLastTranscriptText,
  } = useSessionStore();

  // Fetch session data
  const { data: sessionData } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId),
    refetchInterval: (query) =>
      query.state.data?.mode === "playing" ? false : 2000,
  });

  // Fetch turns (refetch after 30s to pick up background-generated visual_ids)
  const { data: turnsData } = useQuery({
    queryKey: ["turns", sessionId],
    queryFn: () => getPodcastTurns(sessionId),
    enabled: sessionData?.mode === "playing",
    refetchInterval: (query) => {
      // Refetch a few times to pick up visuals generated in background
      const turns = query.state.data?.turns || [];
      const hasEmptyVisuals = turns.some((t) => !t.visual_id);
      return hasEmptyVisuals ? 5000 : false; // refetch every 5s until all turns have visuals
    },
  });

  // Fetch visuals
  const { data: visuals } = useQuery({
    queryKey: ["visuals", sessionData?.paper_id],
    queryFn: () => getVisuals(sessionData!.paper_id),
    enabled: !!sessionData?.paper_id,
  });

  const turns = turnsData?.turns || [];
  const visualsList = visuals || [];

  // Reset stores on mount (so returning to a session shows fresh state)
  const { reset: resetSession } = useSessionStore();
  const { reset: resetPlayback } = usePlaybackStore();
  useEffect(() => {
    resetSession();
    resetPlayback();
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-save progress on page unload (refresh, close, navigate away)
  useEffect(() => {
    const handleBeforeUnload = () => {
      const idx = usePlaybackStore.getState().currentTurnIndex;
      if (idx > 0) {
        // Use sendBeacon for reliable save on unload
        const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sessions/${sessionId}/save-turn?turn_index=${idx}`;
        navigator.sendBeacon(url);
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [sessionId]);

  // Initialize stores
  useEffect(() => {
    if (sessionData) {
      setSession(sessionData.session_id, sessionData.paper_id);
      setMode(sessionData.mode as any);
    }
  }, [sessionData, setSession, setMode]);

  useEffect(() => {
    if (turns.length > 0) setTurns(turns);
  }, [turns, setTurns]);

  // Audio player
  const {
    play, pause, toggle, interrupt, resume, seekToTurn, skipToTurn, setBlockAdvance, setPlaybackRate,
    currentTurn, isPlaying, playInjectedAudio,
  } = useAudioPlayer(turns);
  const [playbackRate, setPlaybackRateState] = useState(1);

  // Streaming audio (Live API)
  const { playChunk: playStreamingChunk, reset: resetStreaming, stop: stopStreaming, ensureReady: ensureStreamingReady } = useStreamingAudio();

  // Microphone
  const { isRecording, startRecording, stopRecording } = useMicrophone();

  // WebSocket message handler
  const handleWSMessage = useCallback(
    (msg: WSServerMessage) => {
      switch (msg.type) {
        case "user_transcript": {
          // Backend transcribed the voice input — update the placeholder text
          updateLastUserTranscript(msg.text);
          break;
        }

        case "answer": {
          // Add agent response to transcript
          appendTranscript({ speaker: msg.speaker, text: msg.text });

          // Play the answer audio, then wait for resume
          if (msg.audio_url) {
            playInjectedAudio(resolveUrl(msg.audio_url) || msg.audio_url);
          }
          setIsWaiting(false);
          break;
        }

        case "resume": {
          // Host bridge line (TTS fallback path)
          stopStreaming();
          const nextTurnIdx = (msg.from_turn ?? currentTurnIndex) + 1;
          if ("host_bridge_text" in msg && msg.host_bridge_text) {
            appendTranscript({ speaker: "host", text: msg.host_bridge_text });

            if ("host_bridge_audio" in msg && msg.host_bridge_audio) {
              playInjectedAudio(resolveUrl(msg.host_bridge_audio) || msg.host_bridge_audio, () => {
                skipToTurn(nextTurnIdx);
              });
            } else {
              skipToTurn(nextTurnIdx);
            }
          } else {
            skipToTurn(nextTurnIdx);
          }
          break;
        }

        // --- Streaming (Live API) messages ---
        case "audio_chunk": {
          // Decode base64 PCM and play via Web Audio
          const raw = atob(msg.data);
          const bytes = new Uint8Array(raw.length);
          for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
          playStreamingChunk(bytes.buffer);
          setIsWaiting(false);
          setIsRestyleWaiting(false);
          break;
        }

        case "transcript_delta": {
          const cleanText = msg.full_text.replace(/^\[(?:Expert|Skeptic|Host)\]\s*/i, "");

          // Detect speaker from transcript prefix
          const ft = msg.full_text.toLowerCase();
          let detectedSpeaker: string = "expert";
          if (ft.startsWith("[skeptic]")) {
            detectedSpeaker = "skeptic";
            setActiveSpeaker("skeptic");
          } else if (ft.startsWith("[expert]")) {
            detectedSpeaker = "expert";
            setActiveSpeaker("expert");
          } else if (ft.startsWith("[host]")) {
            detectedSpeaker = "host";
            setActiveSpeaker("host");
          }

          // Add/update text in main transcript in real-time
          if (!streamingEntryAddedRef.current && cleanText) {
            appendTranscript({ speaker: detectedSpeaker, text: cleanText });
            streamingEntryAddedRef.current = true;
          } else if (streamingEntryAddedRef.current) {
            updateLastTranscriptText(cleanText);
          }
          break;
        }

        case "answer_complete": {
          // Final text — update the transcript entry with final version
          let answerText = msg.text || "";
          answerText = answerText.replace(/^\[(?:Expert|Skeptic|Host)\]\s*/i, "");
          if (streamingEntryAddedRef.current && answerText) {
            updateLastTranscriptText(answerText);
          } else if (answerText) {
            appendTranscript({ speaker: msg.speaker, text: answerText });
          }
          streamingEntryAddedRef.current = false;
          setStreamingTranscript("");
          setActiveSpeaker(msg.speaker as any);
          setIsRestyleWaiting(false);
          setBlockAdvance(false);
          break;
        }

        case "resume_audio_chunk": {
          const raw2 = atob(msg.data);
          const bytes2 = new Uint8Array(raw2.length);
          for (let i = 0; i < raw2.length; i++) bytes2[i] = raw2.charCodeAt(i);
          playStreamingChunk(bytes2.buffer);
          setActiveSpeaker("host");
          break;
        }

        case "resume_transcript_delta": {
          const resumeClean = (streamingTranscript + msg.text).replace(/^\[(?:Expert|Skeptic|Host)\]\s*/i, "");
          // Add host transition to main transcript in real-time
          if (!streamingEntryAddedRef.current && resumeClean) {
            appendTranscript({ speaker: "host", text: resumeClean });
            streamingEntryAddedRef.current = true;
          } else if (streamingEntryAddedRef.current) {
            updateLastTranscriptText(resumeClean);
          }
          setStreamingTranscript((prev) => prev + msg.text);
          break;
        }

        case "resume_from_turn": {
          // Backend tells us which turn to resume from (skipping the interrupted one)
          resumeFromTurnRef.current = msg.turn_index;
          break;
        }

        case "resume_complete": {
          // Finalize host transition text
          if (streamingTranscript && streamingEntryAddedRef.current) {
            const cleanText = streamingTranscript.replace(/^\[(?:Expert|Skeptic|Host)\]\s*/i, "");
            updateLastTranscriptText(cleanText);
          } else if (streamingTranscript) {
            const cleanText = streamingTranscript.replace(/^\[(?:Expert|Skeptic|Host)\]\s*/i, "");
            appendTranscript({ speaker: "host", text: cleanText });
          }
          setStreamingTranscript("");
          isRestyleResponseRef.current = false;
          streamingEntryAddedRef.current = false;
          setBlockAdvance(false);
          // Stop streaming audio before starting podcast turn (prevent overlap)
          stopStreaming();
          // Skip to the next turn immediately
          const targetTurn = resumeFromTurnRef.current;
          resumeFromTurnRef.current = null;
          if (targetTurn !== null && targetTurn < turns.length) {
            skipToTurn(targetTurn);
          } else {
            skipToTurn(currentTurnIndex + 1);
          }
          break;
        }

        // --- Non-streaming (TTS fallback) messages ---
        case "quiz_question": {
          setQuizQuestion({ question_id: msg.question_id, text: msg.text });
          setQuizFeedback(null);
          setQuizWaiting(false);
          setIsWaiting(false);  // Clear so 30s safety timeout doesn't auto-resume
          break;
        }

        case "quiz_feedback": {
          setQuizFeedback({
            correct: msg.correct,
            explanation: msg.explanation,
            weak_concepts: msg.weak_concepts,
          });
          setQuizWaiting(false);
          if (msg.audio_url) playInjectedAudio(resolveUrl(msg.audio_url) || msg.audio_url);
          break;
        }

        // --- Restyle (background regeneration) messages ---
        case "restyle_started": {
          // Restyle manager running in background — silently swaps turns
          break;
        }

        case "turn_update": {
          // Silently swap the turn — if user reaches it, they get the restyled version
          updateTurn(msg.index, {
            index: msg.index,
            speaker: msg.speaker as any,
            text: msg.text,
            audio_url: resolveUrl(msg.audio_url),
            visual_id: msg.visual_id,
            section: msg.section,
          });
          break;
        }

        case "restyle_complete": {
          break;
        }

        case "error": {
          console.error("WS error:", msg.message);
          setIsWaiting(false);
          setIsRestyleWaiting(false);
          setBlockAdvance(false);
          isRestyleResponseRef.current = false;
          streamingEntryAddedRef.current = false;
          // Skip to next turn on error, don't replay interrupted one
          skipToTurn(usePlaybackStore.getState().currentTurnIndex + 1);
          break;
        }
      }
    },
    [appendTranscript, updateLastUserTranscript, playInjectedAudio, playStreamingChunk, setActiveSpeaker, streamingTranscript, resume, play, skipToTurn, currentTurnIndex, turns.length, updateTurn]
  );

  // WebSocket connection
  const { sendInterrupt, sendVoiceInterrupt, sendSimplify, sendGoDeeper, sendQuizStart, sendQuizAnswer, isConnected } =
    useWebSocket({
      sessionId: sessionData?.mode === "playing" ? sessionId : null,
      onMessage: handleWSMessage,
      onDisconnect: () => {
        // Clear stuck waiting state if WS drops during an interaction
        if (isWaiting) {
          setIsWaiting(false);
          skipToTurn(usePlaybackStore.getState().currentTurnIndex + 1);
        }
      },
    });

  // Handle text interrupt
  function handleInterrupt(question: string) {
    interrupt();
    stopStreaming();  // Stop any playing streaming audio (Live API response)
    streamingEntryAddedRef.current = false;
    appendTranscript({ speaker: "user", text: question, isUser: true });
    setIsWaiting(true);
    sendInterrupt(question, currentTurnIndex);
  }

  // Handle voice interrupt (mic toggle)
  async function handleVoiceToggle() {
    if (isRecording) {
      // Stop recording and send audio to backend
      const pcmBuffer = stopRecording();
      interrupt();
      stopStreaming();
      appendTranscript({ speaker: "user", text: "🎤 Voice question...", isUser: true });
      setIsWaiting(true);

      // Convert to base64
      const bytes = new Uint8Array(pcmBuffer);
      let binary = "";
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      const base64 = btoa(binary);

      sendVoiceInterrupt(base64, currentTurnIndex, 16000);
    } else {
      // Start recording — pause podcast while user talks
      interrupt();
      resetStreaming();
      await startRecording();
    }
  }

  // Handle quick actions
  function handleQuickAction(action: string) {
    if (action === "simplify" || action === "go_deeper") {
      const sendFn = action === "simplify" ? sendSimplify : sendGoDeeper;
      const toastMsg = action === "simplify" ? "Simplifying..." : "Going deeper...";
      toast(toastMsg, { duration: 3000 });

      // Unlock Web Audio context during user gesture (click)
      ensureStreamingReady();

      // Pause immediately and send WS message — don't wait for turn to finish
      interrupt();
      setIsRestyleWaiting(true);
      streamingEntryAddedRef.current = false;
      isRestyleResponseRef.current = true;
      sendFn(currentTurnIndex);
    } else if (action === "quiz") {
      interrupt();
      stopStreaming();
      setIsWaiting(true);
      setQuizOpen(true);
      setQuizQuestion(null);
      setQuizFeedback(null);
      setQuizWaiting(true);
      sendQuizStart(currentSection, currentTurnIndex);
    }
  }

  // Loading state
  if (!sessionData || sessionData.mode === "processing") {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
          <p className="text-gray-400">Preparing your podcast...</p>
          <p className="text-gray-600 text-xs">Generating script and voices...</p>
        </div>
      </main>
    );
  }

  // Ready but not started — show paper title and start button
  if (!isPlaying && transcript.length === 0) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-8 max-w-lg px-6">
          {/* Ambient glow */}
          <div className="relative mx-auto w-fit">
            <div className="absolute -inset-16 bg-blue-500/[0.06] rounded-full blur-3xl pointer-events-none" />
            <div className="relative space-y-3">
              <h2 className="text-2xl font-bold">{sessionData.paper_title}</h2>
              <p className="text-gray-400 text-sm">
                {turns.length > 0
                  ? `${turns.length} discussion turns ready`
                  : "Loading turns..."}
              </p>
            </div>
          </div>
          {sessionData.current_turn_index > 0 && turns.length > 0 ? (
            <>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    // Pre-populate transcript with turns BEFORE saved position
                    // (skipToTurn will add the current turn via loadTurn)
                    for (let i = 0; i < sessionData.current_turn_index; i++) {
                      const t = turns[i];
                      if (t) appendTranscript({ speaker: t.speaker, text: t.text });
                    }
                    skipToTurn(sessionData.current_turn_index);
                  }}
                  className="px-6 py-3 rounded-xl bg-white text-black font-medium hover:bg-gray-200 transition-colors shadow-lg shadow-white/10"
                >
                  Resume from turn {sessionData.current_turn_index + 1} / {turns.length}
                </button>
                <button
                  onClick={play}
                  className="px-6 py-3 rounded-xl bg-white/10 text-white font-medium hover:bg-white/20 transition-colors border border-white/20"
                >
                  Start from beginning
                </button>
              </div>
              <p className="text-gray-600 text-xs">You have a saved position</p>
            </>
          ) : (
            <>
              <div className="relative mx-auto w-fit">
                <div className="absolute inset-0 bg-white/15 rounded-full blur-xl pointer-events-none" />
                <button
                  onClick={play}
                  disabled={turns.length === 0}
                  className="relative w-20 h-20 rounded-full bg-white text-gray-900 flex items-center justify-center hover:bg-gray-100 transition-all hover:scale-105 active:scale-95 shadow-2xl shadow-white/20 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {turns.length === 0 ? (
                    <Loader2 className="w-6 h-6 animate-spin" />
                  ) : (
                    <svg className="w-7 h-7 ml-1" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="text-gray-600 text-xs">
                {turns.length > 0 ? "Press play to start" : "Fetching podcast data..."}
              </p>
            </>
          )}
        </div>
      </main>
    );
  }

  const currentVisualId = currentTurn?.visual_id || null;

  return (
    <main className="flex-1 flex flex-col h-screen overflow-hidden">
      <SectionProgress currentSection={currentSection} />

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden xl:mr-[35%]">
        {/* Left: Speakers + Transcript */}
        <SpeakerPanel activeSpeaker={activeSpeaker} isPlaying={isPlaying} />
        <div className="flex-1 min-h-0 overflow-hidden">
          <TranscriptPanel
            entries={transcript}
            currentIndex={transcript.length - 1}
          />
        </div>
      </div>

      {/* Right: Visuals — fixed position, always visible */}
      <div className="hidden xl:block fixed right-0 top-10 bottom-14 w-[35%]">
        <VisualPanel
          visual={activeVisual}
          visuals={visualsList}
          currentVisualId={currentVisualId}
        />
      </div>


      {/* Controls */}
      <ControlBar
        isPlaying={isPlaying}
        currentSection={currentSection}
        currentTurnIndex={currentTurnIndex}
        totalTurns={turns.length}
        onToggle={() => {
          // Always stop streaming audio when toggling
          stopStreaming();
          toggle();
        }}
        onInterrupt={handleInterrupt}
        onQuickAction={handleQuickAction}
        onVoiceToggle={handleVoiceToggle}
        isRecording={isRecording}
        playbackRate={playbackRate}
        onPlaybackRateChange={(rate) => {
          setPlaybackRate(rate);
          setPlaybackRateState(rate);
        }}
        onSave={async () => {
          const { saveProgress } = await import("@/lib/api");
          await saveProgress(sessionId, currentTurnIndex);
          toast.success("Progress saved!", { duration: 2000 });
        }}
        onEndSession={() => {
          pause();
          router.push(`/session/${sessionId}/recap?turn=${currentTurnIndex}`);
        }}
        onExit={() => {
          pause();
          stopStreaming();
          const choice = window.confirm("Save your progress before leaving?");
          if (choice) {
            import("@/lib/api").then(({ saveProgress: sp }) => {
              sp(sessionId, currentTurnIndex).then(() => {
                toast.success("Progress saved!");
                router.push("/");
              });
            });
          } else {
            router.push("/");
          }
        }}
      />

      {/* Waiting indicators */}
      {isWaiting && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
          <span className="text-sm text-gray-300">Thinking...</span>
        </div>
      )}
      {isRestyleWaiting && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm z-10">
          <div className="bg-gray-900 border border-white/10 rounded-2xl px-8 py-6 flex flex-col items-center gap-3 shadow-2xl">
            <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
            <p className="text-white font-medium">Adjusting style...</p>
            <p className="text-gray-400 text-sm">Generating next turn</p>
          </div>
        </div>
      )}

      {/* Quiz Overlay */}
      <QuizOverlay
        isOpen={quizOpen}
        question={quizQuestion}
        feedback={quizFeedback}
        isWaiting={quizWaiting}
        onAnswer={(qid, answer) => {
          setQuizWaiting(true);
          setQuizFeedback(null);
          sendQuizAnswer(qid, answer);
        }}
        onNextQuestion={() => {
          setQuizQuestion(null);
          setQuizFeedback(null);
          setQuizWaiting(true);
          sendQuizStart(currentSection, currentTurnIndex);
        }}
        onClose={() => {
          setQuizOpen(false);
          setQuizQuestion(null);
          setQuizFeedback(null);
          resume();
        }}
      />
    </main>
  );
}
