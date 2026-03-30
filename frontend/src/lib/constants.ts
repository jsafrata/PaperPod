import type { SpeakerRole } from "./types";

export const SPEAKER_CONFIG: Record<
  SpeakerRole,
  {
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    glowColor: string;
    ringBorderColor: string;
    solidBgColor: string;
    hexColor: string;
    gradientBg: string;
    emoji: string;
  }
> = {
  host: {
    label: "Host",
    color: "text-blue-400",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/40",
    glowColor: "shadow-blue-500/40",
    ringBorderColor: "border-blue-400",
    solidBgColor: "bg-blue-400",
    hexColor: "#60a5fa",
    gradientBg: "from-blue-500/[0.08] to-blue-400/[0.02]",
    emoji: "🎙️",
  },
  expert: {
    label: "Expert",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/40",
    glowColor: "shadow-emerald-500/40",
    ringBorderColor: "border-emerald-400",
    solidBgColor: "bg-emerald-400",
    hexColor: "#34d399",
    gradientBg: "from-emerald-500/[0.08] to-emerald-400/[0.02]",
    emoji: "🧠",
  },
  skeptic: {
    label: "Skeptic",
    color: "text-amber-400",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/40",
    glowColor: "shadow-amber-500/40",
    ringBorderColor: "border-amber-400",
    solidBgColor: "bg-amber-400",
    hexColor: "#fbbf24",
    gradientBg: "from-amber-500/[0.08] to-amber-400/[0.02]",
    emoji: "🔍",
  },
};

export const SECTION_LABELS: Record<string, string> = {
  intro: "Introduction",
  method: "Methods",
  results: "Results",
  limitations: "Limitations",
};

export const SECTIONS = ["intro", "method", "results", "limitations"];

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
