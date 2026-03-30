"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, BookOpen, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FlashcardDeck } from "@/components/recap/FlashcardDeck";
import { getRecap } from "@/lib/api";

export default function RecapPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = params.id as string;
  const turnIndex = searchParams.get("turn") ? parseInt(searchParams.get("turn")!) : undefined;

  const { data: recap, isLoading } = useQuery({
    queryKey: ["recap", sessionId, turnIndex],
    queryFn: () => getRecap(sessionId, turnIndex),
  });

  if (isLoading) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <Sparkles className="w-8 h-8 text-blue-400 mx-auto animate-pulse" />
          <p className="text-gray-400">Generating your recap...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl mx-auto p-6 space-y-6 pb-20"
      >
        {/* Header */}
        <div className="text-center space-y-2">
          <BookOpen className="w-10 h-10 text-blue-400 mx-auto" />
          <h2 className="text-3xl font-bold">Session Recap</h2>
          <p className="text-gray-400">Here&apos;s what you covered</p>
        </div>

        {/* Key Takeaways */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="p-6 space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <span className="text-blue-400">💡</span> Key Takeaways
            </h3>
            <ol className="space-y-3">
              {(recap?.takeaways || []).map((t, i) => (
                <li key={i} className="flex gap-3">
                  <span className="text-blue-400 font-bold text-lg">{i + 1}.</span>
                  <span className="text-gray-300 leading-relaxed">{t}</span>
                </li>
              ))}
            </ol>
          </Card>
        </motion.div>

        {/* Limitations */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="p-6 space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <span className="text-amber-400">⚠️</span> Limitations
            </h3>
            <ul className="space-y-2">
              {(recap?.limitations || []).map((l, i) => (
                <li key={i} className="flex gap-2 text-gray-300">
                  <span className="text-amber-400">•</span>
                  <span>{l}</span>
                </li>
              ))}
            </ul>
          </Card>
        </motion.div>

        {/* Flashcards */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <FlashcardDeck flashcards={recap?.flashcards || []} />
        </motion.div>

        {/* Weak Concepts */}
        {recap?.weak_concepts && recap.weak_concepts.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <Card className="p-6 space-y-3">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <span className="text-red-400">📌</span> Areas to Review
              </h3>
              <div className="flex flex-wrap gap-2">
                {recap.weak_concepts.map((c, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 bg-amber-500/15 text-amber-300 rounded-lg text-sm"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

        {/* Actions */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex items-center justify-center gap-4 pt-4"
        >
          <Button variant="secondary" onClick={() => router.push(`/session/${sessionId}`)}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to podcast
          </Button>
          <Button onClick={() => router.push("/")}>
            Start new paper
          </Button>
        </motion.div>
      </motion.div>
    </main>
  );
}
