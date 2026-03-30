"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, XCircle, Loader2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface QuizOverlayProps {
  isOpen: boolean;
  question: { question_id: string; text: string } | null;
  feedback: { correct: boolean; explanation: string; weak_concepts: string[] } | null;
  isWaiting: boolean;
  onAnswer: (questionId: string, answer: string) => void;
  onNextQuestion: () => void;
  onClose: () => void;
}

export function QuizOverlay({
  isOpen,
  question,
  feedback,
  isWaiting,
  onAnswer,
  onNextQuestion,
  onClose,
}: QuizOverlayProps) {
  const [userAnswer, setUserAnswer] = useState("");

  function handleSubmit() {
    if (!question || !userAnswer.trim()) return;
    onAnswer(question.question_id, userAnswer.trim());
    setUserAnswer("");
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6"
        >
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="w-full max-w-lg"
          >
            <Card className="p-6 space-y-5">
              {/* Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Quiz Mode</h3>
                <button
                  onClick={onClose}
                  className="text-gray-500 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Question */}
              {question && !feedback && (
                <div className="space-y-4">
                  <p className="text-white text-base leading-relaxed">
                    {question.text}
                  </p>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={userAnswer}
                      onChange={(e) => setUserAnswer(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                      placeholder="Type your answer..."
                      autoFocus
                      disabled={isWaiting}
                      className="flex-1 h-10 px-4 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    />
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={handleSubmit}
                        disabled={!userAnswer.trim() || isWaiting}
                      >
                        {isWaiting ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          "Submit"
                        )}
                      </Button>
                      <span className="text-[10px] text-gray-600">Enter ↵</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Feedback */}
              {feedback && (
                <div className="space-y-4">
                  <div
                    className={`flex items-start gap-3 p-4 rounded-lg ${
                      feedback.correct
                        ? "bg-emerald-500/10 border border-emerald-500/20"
                        : "bg-red-500/10 border border-red-500/20"
                    }`}
                  >
                    {feedback.correct ? (
                      <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className={`font-medium text-sm ${feedback.correct ? "text-emerald-400" : "text-red-400"}`}>
                        {feedback.correct ? "Correct!" : "Not quite"}
                      </p>
                      <p className="text-gray-300 text-sm mt-1">
                        {feedback.explanation}
                      </p>
                    </div>
                  </div>

                  {/* Weak concepts */}
                  {feedback.weak_concepts.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Areas to review:</p>
                      <div className="flex flex-wrap gap-1">
                        {feedback.weak_concepts.map((c, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-amber-500/15 text-amber-300 rounded text-xs"
                          >
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button onClick={onNextQuestion} variant="secondary">
                      <ArrowRight className="w-4 h-4 mr-1" />
                      Next question
                    </Button>
                    <Button onClick={onClose} variant="ghost">
                      Back to podcast
                    </Button>
                  </div>
                </div>
              )}

              {/* Loading state */}
              {isWaiting && !question && !feedback && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                  <span className="ml-2 text-gray-400">Loading question...</span>
                </div>
              )}
            </Card>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
