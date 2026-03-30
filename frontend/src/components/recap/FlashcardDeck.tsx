"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { Flashcard } from "@/lib/types";

interface FlashcardDeckProps {
  flashcards: Flashcard[];
}

export function FlashcardDeck({ flashcards }: FlashcardDeckProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  if (flashcards.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-2">Flashcards</h3>
        <p className="text-gray-500 text-sm">No flashcards generated for this session.</p>
      </Card>
    );
  }

  const card = flashcards[currentIndex];

  function next() {
    setIsFlipped(false);
    setCurrentIndex((i) => (i + 1) % flashcards.length);
  }

  function prev() {
    setIsFlipped(false);
    setCurrentIndex((i) => (i - 1 + flashcards.length) % flashcards.length);
  }

  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Flashcards</h3>
        <span className="text-sm text-gray-500">
          {currentIndex + 1} / {flashcards.length}
        </span>
      </div>

      {/* Card */}
      <div
        onClick={() => setIsFlipped(!isFlipped)}
        className="cursor-pointer"
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={`${currentIndex}-${isFlipped}`}
            initial={{ rotateY: 90, opacity: 0 }}
            animate={{ rotateY: 0, opacity: 1 }}
            exit={{ rotateY: -90, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className={`min-h-[140px] p-6 rounded-xl border flex items-center justify-center text-center ${
              isFlipped
                ? "bg-emerald-500/10 border-emerald-500/20"
                : "bg-white/5 border-white/10"
            }`}
          >
            <div>
              <p className="text-xs text-gray-500 mb-2">
                {isFlipped ? "Answer" : "Question"} · tap to flip
              </p>
              <p className={`text-base ${isFlipped ? "text-emerald-300" : "text-white"}`}>
                {isFlipped ? card.back : card.front}
              </p>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={prev}
          className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button
          onClick={() => setIsFlipped(!isFlipped)}
          className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
        >
          <RotateCcw className="w-5 h-5" />
        </button>
        <button
          onClick={next}
          className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </Card>
  );
}
