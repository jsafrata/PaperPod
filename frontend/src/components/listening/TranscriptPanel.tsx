"use client";

import { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { SPEAKER_CONFIG } from "@/lib/constants";
import type { SpeakerRole } from "@/lib/types";

interface TranscriptEntry {
  speaker: string;
  text: string;
  isUser?: boolean;
}

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
  currentIndex: number;
}

const SPEAKER_EMOJI: Record<string, string> = {
  host: "🎙️",
  expert: "🧠",
  skeptic: "🔍",
};

export function TranscriptPanel({ entries, currentIndex }: TranscriptPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  return (
    <div className="h-full overflow-y-auto px-4 py-3">
      {entries.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full gap-3 opacity-40">
          <div className="w-12 h-12 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-gray-600" />
          </div>
          <p className="text-gray-600 text-sm text-center">
            Transcript will appear here<br />when the podcast starts
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          {entries.map((entry, i) => {
            const isActive = i === currentIndex;
            const isPast = i < currentIndex;
            const config = entry.isUser
              ? null
              : SPEAKER_CONFIG[entry.speaker as SpeakerRole];
            const emoji = entry.isUser ? "💬" : SPEAKER_EMOJI[entry.speaker] || "🗣️";
            const accentColor = entry.isUser ? "#a78bfa" : config?.hexColor || "#6b7280";

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className={cn(
                  "relative flex gap-3 py-3 px-4 rounded-xl transition-all duration-300",
                  isActive && "bg-white/[0.05]",
                  isPast && "opacity-50",
                )}
              >
                {/* Left accent bar */}
                <div
                  className={cn(
                    "absolute left-0 top-3 bottom-3 w-[3px] rounded-full transition-all duration-300",
                    isActive ? "opacity-100" : "opacity-0",
                  )}
                  style={{ backgroundColor: accentColor }}
                />

                {/* Mini avatar */}
                <div
                  className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs mt-0.5"
                  style={{ backgroundColor: `${accentColor}15` }}
                >
                  {emoji}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-xs font-semibold",
                        entry.isUser ? "text-purple-400" : config?.color || "text-gray-400",
                      )}
                    >
                      {entry.isUser ? "You" : config?.label || entry.speaker}
                    </span>
                    <span className="text-[10px] text-gray-700 font-mono">
                      #{i + 1}
                    </span>
                  </div>
                  <p className={cn(
                    "text-[13px] mt-1 leading-relaxed",
                    isActive ? "text-gray-200" : "text-gray-500",
                  )}>
                    {entry.text}
                  </p>
                </div>
              </motion.div>
            );
          })}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
