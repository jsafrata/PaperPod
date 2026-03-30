"use client";

import { cn } from "@/lib/utils";
import { forwardRef, type ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[#030712] disabled:pointer-events-none disabled:opacity-40",
          {
            "bg-white text-gray-900 hover:bg-gray-100 active:scale-[0.98] shadow-lg shadow-white/5": variant === "primary",
            "bg-white/[0.06] text-gray-300 hover:bg-white/[0.1] hover:text-white border border-white/[0.1] hover:border-white/[0.15]": variant === "secondary",
            "text-gray-500 hover:text-white hover:bg-white/[0.06]": variant === "ghost",
          },
          {
            "h-8 px-3 text-xs": size === "sm",
            "h-10 px-4 text-sm": size === "md",
            "h-12 px-6 text-sm": size === "lg",
          },
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";
export { Button };
