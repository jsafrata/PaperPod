"use client";

import { useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Check, Circle, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { getPaperStatus } from "@/lib/api";

const stepIcons: Record<string, string> = {
  "Reading paper": "📄",
  "Extracting visuals": "🖼️",
  "Building explanations": "🧠",
  "Writing script": "✍️",
  "Generating voices": "🎙️",
  "Preparing quiz": "📝",
};

export default function ProcessingPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = params.id as string;
  const paperId = searchParams.get("paper_id") || "";

  const { data: status } = useQuery({
    queryKey: ["paper-status", paperId],
    queryFn: () => getPaperStatus(paperId),
    refetchInterval: 2000,
    enabled: !!paperId,
  });

  useEffect(() => {
    if (status?.status === "ready") {
      const timer = setTimeout(() => {
        router.push(`/session/${sessionId}`);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [status, sessionId, router]);

  const steps = status?.steps || [];
  const completedCount = steps.filter((s) => s.status === "done").length;
  const progress = steps.length > 0 ? (completedCount / steps.length) * 100 : 0;

  return (
    <main className="flex-1 flex items-center justify-center p-6">
      <div className="w-full max-w-4xl flex gap-8 items-start">
        {/* Left: Loading steps */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md space-y-8"
        >
          {/* Header */}
          <div className="text-center space-y-2">
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="inline-block"
            >
              <Sparkles className="w-10 h-10 text-blue-400 mx-auto" />
            </motion.div>
            <h2 className="text-2xl font-bold">Preparing your podcast</h2>
            <p className="text-gray-400 text-sm">{status?.title || "Processing paper..."}</p>
          </div>

          {/* Progress bar */}
          <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            />
          </div>

          {/* Steps */}
          <div className="space-y-3">
            {steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1, duration: 0.3 }}
                className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                  step.status === "running"
                    ? "bg-white/5"
                    : ""
                }`}
              >
                {/* Icon */}
                <div className="w-8 h-8 flex items-center justify-center">
                  {step.status === "done" && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 500 }}
                    >
                      <Check className="w-5 h-5 text-emerald-400" />
                    </motion.div>
                  )}
                  {step.status === "running" && (
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                  )}
                  {step.status === "pending" && (
                    <Circle className="w-5 h-5 text-gray-700" />
                  )}
                </div>

                {/* Label */}
                <span
                  className={`text-sm ${
                    step.status === "done"
                      ? "text-gray-400"
                      : step.status === "running"
                      ? "text-white font-medium"
                      : "text-gray-600"
                  }`}
                >
                  {step.name}
                </span>

                {/* Emoji */}
                <span className="ml-auto text-lg">
                  {stepIcons[step.name] || ""}
                </span>
              </motion.div>
            ))}
          </div>

          {/* Status message */}
          {status?.status === "failed" && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center p-4 bg-red-500/10 border border-red-500/20 rounded-lg"
            >
              <p className="text-red-400 text-sm">
                Processing failed. Please try uploading again.
              </p>
            </motion.div>
          )}
        </motion.div>

        {/* Right: Paper summary */}
        {status?.summary && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex-1 max-w-sm sticky top-6"
          >
            <div className="p-5 bg-white/5 border border-white/10 rounded-xl space-y-3">
              <p className="text-xs font-semibold text-blue-400 uppercase tracking-wide">Paper Summary</p>
              <p className="text-sm text-gray-300 leading-relaxed">{status.summary}</p>
            </div>
          </motion.div>
        )}
      </div>
    </main>
  );
}
