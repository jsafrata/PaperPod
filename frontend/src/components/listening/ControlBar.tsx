"use client";

import { Play, Pause, MessageCircle, ChevronDown, ChevronUp, HelpCircle, BookOpen, Mic, X, Save } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { SECTION_LABELS } from "@/lib/constants";

interface ControlBarProps {
  isPlaying: boolean;
  currentSection: string;
  currentTurnIndex: number;
  totalTurns: number;
  onToggle: () => void;
  onInterrupt: (question: string) => void;
  onQuickAction: (action: string) => void;
  onEndSession?: () => void;
  onSave?: () => void;
  onExit?: () => void;
  onVoiceToggle?: () => void;
  isRecording?: boolean;
  playbackRate?: number;
  onPlaybackRateChange?: (rate: number) => void;
}

export function ControlBar({
  isPlaying,
  currentSection,
  currentTurnIndex,
  totalTurns,
  onToggle,
  onInterrupt,
  onQuickAction,
  onEndSession,
  onSave,
  onExit,
  onVoiceToggle,
  isRecording,
  playbackRate = 1,
  onPlaybackRateChange,
}: ControlBarProps) {
  const [showInput, setShowInput] = useState(false);
  const [question, setQuestion] = useState("");

  function handleSubmit() {
    if (question.trim()) {
      onInterrupt(question.trim());
      setQuestion("");
      setShowInput(false);
    }
  }

  return (
    <div className="border-t border-white/[0.08] bg-gradient-to-t from-[#030712] via-[#0a1120] to-[#0a1120]/80 backdrop-blur-xl flex-shrink-0">
      {/* Expandable text input */}
      <AnimatePresence>
        {showInput && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-6 pt-3 pb-1 flex gap-3">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                placeholder="Ask anything about this paper..."
                autoFocus
                className="flex-1 h-11 px-4 bg-white/[0.04] border border-white/[0.1] rounded-xl text-white text-sm placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/30 transition-all"
              />
              <Button size="md" onClick={handleSubmit} disabled={!question.trim()}>
                Send
              </Button>
              <button
                onClick={() => setShowInput(false)}
                className="p-2 rounded-lg text-gray-600 hover:text-gray-300 hover:bg-white/[0.06] transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main controls */}
      <div className="px-6 py-3 flex items-center gap-3">
        {/* LEFT: Playback */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggle}
            className="w-12 h-12 rounded-full bg-white text-gray-900 flex items-center justify-center hover:bg-gray-100 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-white/10"
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5 ml-0.5" />
            )}
          </button>

          {/* Speed control */}
          {onPlaybackRateChange && (
            <button
              onClick={() => {
                const rates = [1, 1.25, 1.5, 2];
                const next = rates[(rates.indexOf(playbackRate) + 1) % rates.length];
                onPlaybackRateChange(next);
              }}
              className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] text-gray-400 hover:text-white hover:bg-white/[0.08] transition-all text-xs font-mono font-bold"
            >
              {playbackRate}x
            </button>
          )}

          <div className="flex flex-col">
            <span className="px-2.5 py-0.5 rounded-lg bg-blue-500/10 text-blue-300 text-[11px] font-medium w-fit">
              {SECTION_LABELS[currentSection] || currentSection}
            </span>
            <span className="text-[11px] text-gray-600 mt-0.5 pl-1 font-mono">
              {currentTurnIndex + 1}/{totalTurns}
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-white/[0.08]" />

        {/* CENTER: Quick actions */}
        <div className="flex-1 flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => onQuickAction("simplify")}>
            <ChevronDown className="w-3.5 h-3.5 mr-1.5" />
            Simplify
          </Button>
          <Button size="sm" variant="secondary" onClick={() => onQuickAction("go_deeper")}>
            <ChevronUp className="w-3.5 h-3.5 mr-1.5" />
            Go Deeper
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onQuickAction("quiz")}>
            <HelpCircle className="w-3.5 h-3.5 mr-1.5" />
            Quiz
          </Button>
        </div>

        {/* RIGHT: Interaction + session */}
        <div className="flex items-center gap-1.5">
          {/* Mic */}
          {onVoiceToggle && (
            <button
              onClick={onVoiceToggle}
              className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center transition-all",
                isRecording
                  ? "bg-blue-500/20 text-blue-400 border border-blue-400/40 shadow-lg shadow-blue-500/20"
                  : "bg-white/[0.04] text-gray-500 border border-white/[0.06] hover:text-white hover:bg-white/[0.08]"
              )}
            >
              <Mic className="w-4 h-4" />
            </button>
          )}

          {/* Ask */}
          <button
            onClick={() => setShowInput(!showInput)}
            className={cn(
              "h-10 px-4 rounded-xl text-sm font-medium flex items-center gap-2 transition-all",
              showInput
                ? "bg-blue-500/15 text-blue-300 border border-blue-500/25"
                : "bg-white/[0.04] text-gray-500 border border-white/[0.06] hover:text-white hover:bg-white/[0.08]"
            )}
          >
            <MessageCircle className="w-4 h-4" />
            Ask
          </button>

          {/* Divider */}
          <div className="w-px h-6 bg-white/[0.06] mx-1" />

          {/* Session controls (icon-only) */}
          {onEndSession && (
            <button
              onClick={onEndSession}
              className="p-2.5 rounded-xl text-gray-600 hover:text-gray-300 hover:bg-white/[0.06] transition-all"
              title="View recap"
            >
              <BookOpen className="w-4 h-4" />
            </button>
          )}
          {onSave && (
            <button
              onClick={onSave}
              className="p-2.5 rounded-xl text-gray-600 hover:text-gray-300 hover:bg-white/[0.06] transition-all"
              title="Save progress"
            >
              <Save className="w-4 h-4" />
            </button>
          )}
          {onExit && (
            <button
              onClick={onExit}
              className="p-2.5 rounded-xl text-gray-600 hover:text-red-400 hover:bg-red-500/[0.06] transition-all"
              title="Exit"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
