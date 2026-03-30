"use client";

import { RefreshCw } from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";

export function RestyleIndicator() {
  const activeRestyle = useSessionStore((s) => s.activeRestyle);
  const restyleProgress = useSessionStore((s) => s.restyleProgress);

  if (!activeRestyle) return null;

  const progressText = restyleProgress
    ? `${restyleProgress.done}/${restyleProgress.total} turns`
    : "starting...";

  return (
    <div className="px-4 py-2 bg-blue-500/10 border-t border-blue-500/20 flex items-center gap-3 text-sm">
      <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
      <span className="text-blue-300">
        Restyling: <span className="text-white">{activeRestyle}</span>
      </span>
      <span className="text-blue-400/60">{progressText}</span>
    </div>
  );
}
