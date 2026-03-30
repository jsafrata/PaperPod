"use client";

import { cn } from "@/lib/utils";
import { SECTION_LABELS, SECTIONS } from "@/lib/constants";

interface SectionProgressProps {
  currentSection: string;
}

export function SectionProgress({ currentSection }: SectionProgressProps) {
  const currentIdx = SECTIONS.indexOf(currentSection);

  return (
    <div className="flex items-center px-6 py-2.5 border-b border-white/[0.06] bg-[#0a1120]/40 flex-shrink-0">
      {SECTIONS.map((section, i) => {
        const isPast = i < currentIdx;
        const isCurrent = i === currentIdx;

        return (
          <div key={section} className="flex items-center flex-1">
            <div className={cn(
              "flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-medium tracking-wide transition-all duration-500",
              isCurrent && "bg-blue-500/15 text-blue-300",
              isPast && "text-emerald-400/70",
              !isPast && !isCurrent && "text-gray-600",
            )}>
              <div className={cn(
                "w-1.5 h-1.5 rounded-full transition-colors duration-500",
                isCurrent && "bg-blue-400",
                isPast && "bg-emerald-500",
                !isPast && !isCurrent && "bg-gray-700",
              )} />
              {SECTION_LABELS[section]}
            </div>

            {i < SECTIONS.length - 1 && (
              <div className="flex-1 mx-2">
                <div className={cn(
                  "h-px transition-colors duration-500",
                  isPast ? "bg-emerald-500/30" : "bg-white/[0.06]",
                )} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
