"use client";

import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {}

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-white/[0.08] bg-[#0a1120]/80 backdrop-blur-xl shadow-xl shadow-black/40 ring-1 ring-inset ring-white/[0.03]",
        className
      )}
      {...props}
    />
  );
}
