"use client";

import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "paper" | "ai";
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        {
          "bg-white/10 text-gray-300": variant === "default",
          "bg-gray-600/50 text-gray-300": variant === "paper",
          "bg-purple-500/20 text-purple-300": variant === "ai",
        },
        className
      )}
      {...props}
    />
  );
}
