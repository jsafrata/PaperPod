"use client";

import { SpeakerCard } from "./SpeakerCard";
import type { SpeakerRole } from "@/lib/types";

interface SpeakerPanelProps {
  activeSpeaker: SpeakerRole | null;
  isPlaying?: boolean;
}

const SPEAKERS: SpeakerRole[] = ["host", "expert", "skeptic"];

export function SpeakerPanel({ activeSpeaker, isPlaying }: SpeakerPanelProps) {
  return (
    <div className="flex gap-2 p-4 pb-3 border-b border-white/[0.06] flex-shrink-0">
      {SPEAKERS.map((role) => (
        <SpeakerCard
          key={role}
          role={role}
          isActive={activeSpeaker === role}
          isPlaying={isPlaying}
        />
      ))}
    </div>
  );
}
