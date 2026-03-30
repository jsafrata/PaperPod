"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Check, Circle, Sparkles, Lightbulb, FlaskConical, TrendingUp, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { getPaperStatus, createSession, getSession } from "@/lib/api";
import type { SessionData } from "@/lib/types";

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
  const paperId = params.paperId as string;
  const difficulty = searchParams.get("difficulty") || "beginner";
  const length = searchParams.get("length") || "standard";

  const [sessionId, setSessionId] = useState<string | null>(null);

  // Poll paper status (includes session_id once auto-created)
  const { data: paperStatus } = useQuery({
    queryKey: ["paper-status", paperId],
    queryFn: () => getPaperStatus(paperId),
    refetchInterval: 2000,
  });

  // Pick up session_id from paper status (auto-created during ingestion)
  useEffect(() => {
    if (paperStatus?.session_id && !sessionId) {
      setSessionId(paperStatus.session_id);
    }
  }, [paperStatus, sessionId]);

  // Fallback: if paper is ready but no session_id in status, create one
  const sessionCreated = useRef(false);
  useEffect(() => {
    if (paperStatus?.status === "ready" && !sessionId && !sessionCreated.current) {
      sessionCreated.current = true;

      const tryCreate = (attempt: number) => {
        createSession(paperId, difficulty).then((session) => {
          setSessionId(session.session_id);
        }).catch((err) => {
          console.error(`Failed to create session (attempt ${attempt}):`, err);
          if (attempt < 3) {
            setTimeout(() => {
              sessionCreated.current = false;
              tryCreate(attempt + 1);
            }, 2000);
          }
        });
      };

      tryCreate(1);
    }
  }, [paperStatus, paperId, difficulty]);

  // Poll session status once we have a session_id
  const { data: sessionData } = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId!),
    refetchInterval: 2000,
    enabled: !!sessionId,
  });

  // Parse structured summary JSON
  const summary = useMemo(() => {
    if (!paperStatus?.summary) return null;
    try {
      return JSON.parse(paperStatus.summary) as {
        one_liner: string;
        key_points: string[];
        method: string;
        finding: string;
        why_it_matters: string;
      };
    } catch {
      // Fallback for plain text summaries
      return { one_liner: paperStatus.summary, key_points: [], method: "", finding: "", why_it_matters: "" };
    }
  }, [paperStatus?.summary]);

  // Use real backend progress — no fake timing
  const allSteps = paperStatus?.steps || [];
  const completedCount = allSteps.filter((s) => s.status === "done").length;
  const progress = allSteps.length > 0 ? (completedCount / allSteps.length) * 100 : 0;

  // Estimated time remaining based on which step we're on
  const stepEstimates: Record<string, string> = {
    "Reading paper": "~10s",
    "Extracting visuals": "~10s",
    "Building explanations": "~60s",
    "Writing script": "~10s",
    "Generating voices": "~30s",
    "Preparing quiz": "~20s",
  };
  const currentStep = allSteps.find((s) => s.status === "running");
  const currentStepIdx = currentStep ? allSteps.indexOf(currentStep) : -1;
  const remainingSteps = allSteps.slice(currentStepIdx >= 0 ? currentStepIdx : 0);
  const estimatedSeconds = remainingSteps.reduce((sum, s) => {
    if (s.status === "done") return sum;
    const est = stepEstimates[s.name];
    return sum + (est ? parseInt(est.replace(/\D/g, "")) : 15);
  }, 0);
  const estimatedTime = estimatedSeconds > 60
    ? `~${Math.ceil(estimatedSeconds / 60)} min remaining`
    : `~${estimatedSeconds}s remaining`;

  // Navigate when session is ready
  useEffect(() => {
    if (sessionData?.mode === "playing" && sessionId) {
      const timer = setTimeout(() => {
        router.push(`/session/${sessionId}`);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [sessionData, sessionId, router]);

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
          <div className="text-center space-y-2">
            <motion.div
              animate={{ rotate: [0, 5, -5, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="inline-block"
            >
              <Sparkles className="w-10 h-10 text-blue-400 mx-auto" />
            </motion.div>
            <h2 className="text-2xl font-bold">Preparing your podcast</h2>
            <p className="text-gray-400 text-sm">{paperStatus?.title || "Processing paper..."}</p>
          </div>

          {/* Progress bar + estimate */}
          <div className="space-y-2">
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-blue-500 to-emerald-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <p className="text-xs text-gray-500 text-center">
              {paperStatus?.status === "ready" ? "Ready!" : estimatedTime}
            </p>
          </div>

          {/* Steps */}
          <div className="space-y-3">
            {allSteps.map((step, i) => (
              <motion.div
                key={step.name}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1, duration: 0.3 }}
                className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                  step.status === "running" ? "bg-white/5" : ""
                }`}
              >
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
                <span className="ml-auto text-lg">
                  {stepIcons[step.name] || ""}
                </span>
              </motion.div>
            ))}
          </div>

          {paperStatus?.status === "failed" && (
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
        {summary && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex-1 max-w-sm sticky top-6 space-y-4"
          >
            {/* One-liner */}
            <div className="p-4 bg-gradient-to-br from-blue-500/10 to-emerald-500/10 border border-white/10 rounded-xl">
              <p className="text-sm text-white font-medium leading-relaxed">{summary.one_liner}</p>
            </div>

            {/* Key points */}
            {summary.key_points.length > 0 && (
              <div className="p-4 bg-white/5 border border-white/10 rounded-xl space-y-3">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-amber-400" />
                  <p className="text-xs font-semibold text-amber-400 uppercase tracking-wide">Key Points</p>
                </div>
                <ul className="space-y-2">
                  {summary.key_points.map((point, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + i * 0.1 }}
                      className="flex items-start gap-2 text-sm text-gray-300"
                    >
                      <span className="text-emerald-400 mt-0.5 shrink-0">&#8226;</span>
                      {point}
                    </motion.li>
                  ))}
                </ul>
              </div>
            )}

            {/* Method + Finding + Why it matters */}
            <div className="space-y-2">
              {summary.method && (
                <motion.div
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  className="flex items-start gap-2.5 p-3 bg-white/5 border border-white/10 rounded-lg"
                >
                  <FlaskConical className="w-4 h-4 text-purple-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-gray-400"><span className="text-purple-400 font-medium">Method: </span>{summary.method}</p>
                </motion.div>
              )}
              {summary.finding && (
                <motion.div
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6 }}
                  className="flex items-start gap-2.5 p-3 bg-white/5 border border-white/10 rounded-lg"
                >
                  <TrendingUp className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-gray-400"><span className="text-emerald-400 font-medium">Finding: </span>{summary.finding}</p>
                </motion.div>
              )}
              {summary.why_it_matters && (
                <motion.div
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                  className="flex items-start gap-2.5 p-3 bg-white/5 border border-white/10 rounded-lg"
                >
                  <Zap className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-gray-400"><span className="text-blue-400 font-medium">Why it matters: </span>{summary.why_it_matters}</p>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </main>
  );
}
