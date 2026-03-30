"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { SPEAKER_CONFIG } from "@/lib/constants";
import type { SpeakerRole } from "@/lib/types";

interface SpeakerCardProps {
  role: SpeakerRole;
  isActive: boolean;
  isPlaying?: boolean;
}

export function SpeakerCard({ role, isActive, isPlaying = true }: SpeakerCardProps) {
  const config = SPEAKER_CONFIG[role];
  const animating = isActive && isPlaying;

  return (
    <motion.div
      layout
      animate={{
        scale: isActive ? 1 : 0.96,
        opacity: isActive ? 1 : 0.5,
      }}
      transition={{ type: "spring", stiffness: 260, damping: 22 }}
      className={cn(
        "relative flex items-center gap-3 px-4 py-3 rounded-2xl border transition-colors duration-300 flex-1",
        isActive && "bg-gradient-to-r",
        isActive && config.gradientBg,
        isActive ? config.borderColor : "border-white/[0.06]",
        !isActive && "bg-white/[0.02]",
      )}
    >
      {/* Ambient glow behind active card */}
      {isActive && (
        <div
          className="absolute inset-0 rounded-2xl blur-xl pointer-events-none animate-glow-pulse"
          style={{ background: `radial-gradient(ellipse at center, ${config.hexColor}12, transparent 70%)` }}
        />
      )}

      {/* Avatar */}
      <div className="relative flex-shrink-0">
        <motion.div
          animate={{ width: isActive ? 44 : 36, height: isActive ? 44 : 36 }}
          transition={{ type: "spring", stiffness: 260, damping: 22 }}
          className="rounded-full flex items-center justify-center"
          style={{
            background: isActive
              ? `linear-gradient(135deg, ${config.hexColor}25, ${config.hexColor}08)`
              : "rgba(255,255,255,0.04)",
            border: isActive ? `2px solid ${config.hexColor}50` : "2px solid rgba(255,255,255,0.06)",
          }}
        >
          <span className="text-base">{config.emoji}</span>
        </motion.div>

        {/* Speaking indicator dot */}
        {animating && (
          <div
            className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#0a1120] animate-speaking-dot"
            style={{ backgroundColor: config.hexColor }}
          />
        )}
      </div>

      {/* Name + audio bars */}
      <div className="flex-1 min-w-0">
        <p className={cn(
          "text-sm font-semibold truncate",
          isActive ? config.color : "text-gray-600",
        )}>
          {config.label}
        </p>

        {/* Audio bars */}
        <div className="flex items-end gap-[2px] mt-1.5 h-3">
          {[0, 1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className={cn("w-[2.5px] rounded-full", animating ? "speaker-bar" : "")}
              style={{
                height: 12,
                backgroundColor: isActive ? `${config.hexColor}80` : "rgba(255,255,255,0.06)",
                animationDelay: animating ? `${i * 0.07}s` : undefined,
                transform: animating ? undefined : isActive ? "scaleY(0.4)" : "scaleY(0.2)",
                transformOrigin: "bottom",
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
