"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ImageIcon } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { Visual } from "@/lib/types";

interface VisualPanelProps {
  visual: Visual | null;
  visuals: Visual[];
  currentVisualId: string | null;
}

export function VisualPanel({ visual, visuals, currentVisualId }: VisualPanelProps) {
  const activeVisual = currentVisualId
    ? visuals.find((v) => v.id === currentVisualId) || visual
    : visual;
  const [imageLoaded, setImageLoaded] = useState(false);

  return (
    <div className="h-full flex flex-col p-4 bg-[#060d1a] border-l border-white/[0.06]">
      {/* Header */}
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500">
          Visuals
        </h3>
        {activeVisual && (
          <Badge variant={activeVisual.provenance === "from_paper" ? "paper" : "ai"}>
            {activeVisual.provenance === "from_paper" ? "From paper" : "AI generated"}
          </Badge>
        )}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {activeVisual ? (
          <motion.div
            key={activeVisual.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
            className="flex-1 flex flex-col min-h-0"
          >
            {/* Image */}
            <div className="flex-1 flex items-center justify-center rounded-2xl overflow-hidden mb-3 min-h-0 relative bg-white/[0.02] border border-white/[0.06]">
              {activeVisual.image_url ? (
                <>
                  {!imageLoaded && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-8 h-8 border-2 border-white/10 border-t-blue-400 rounded-full animate-spin" />
                    </div>
                  )}
                  <img
                    src={activeVisual.image_url}
                    alt={activeVisual.caption || "Paper figure"}
                    className="max-w-full max-h-full object-contain p-3"
                    onLoad={() => setImageLoaded(true)}
                    onError={() => setImageLoaded(true)}
                  />
                </>
              ) : (
                <div className="text-center space-y-2 p-6">
                  <ImageIcon className="w-8 h-8 text-gray-700 mx-auto" />
                  <p className="text-gray-600 text-sm">Image unavailable</p>
                </div>
              )}
            </div>

            {/* Caption */}
            {activeVisual.caption && (
              <p className="text-[11px] text-gray-500 line-clamp-3 leading-relaxed px-1 flex-shrink-0">
                {activeVisual.caption}
              </p>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex-1 flex flex-col items-center justify-center gap-4 opacity-30"
          >
            <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
              <ImageIcon className="w-7 h-7 text-gray-600" />
            </div>
            <div className="text-center">
              <p className="text-gray-500 text-sm font-medium">No visual yet</p>
              <p className="text-gray-600 text-xs mt-1">
                Figures appear as they are discussed
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
