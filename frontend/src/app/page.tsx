"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useQuery } from "@tanstack/react-query";
import { Upload, Link, Loader2, FileText, Play, Trash2, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { uploadPaper, submitArxiv, getRecentSessions } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const router = useRouter();
  const [arxivUrl, setArxivUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("");
  const [difficulty, setDifficulty] = useState<"beginner" | "technical">("beginner");
  const [length, setLength] = useState<"quick" | "standard" | "deep">("standard");

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;
      if (file.type !== "application/pdf") {
        toast.error("Please upload a PDF file");
        return;
      }
      startProcessing(() => uploadPaper(file));
    },
    [difficulty]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: isLoading,
  });

  async function handleArxivSubmit() {
    if (!arxivUrl.trim()) return;
    await startProcessing(() => submitArxiv(arxivUrl.trim(), difficulty, length));
  }

  async function startProcessing(uploadFn: () => Promise<{ paper_id: string }>) {
    setIsLoading(true);
    setLoadingText("Uploading paper...");
    try {
      const { paper_id } = await uploadFn();
      router.push(`/processing/${paper_id}?difficulty=${difficulty}&length=${length}`);
    } catch (err) {
      toast.error("Failed to upload paper. Please try again.");
      console.error(err);
      setIsLoading(false);
      setLoadingText("");
    }
  }

  return (
    <main className="flex-1 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Subtle background gradient orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/[0.03] rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/[0.03] rounded-full blur-[100px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-xl space-y-10 relative z-10"
      >
        {/* Header */}
        <div className="text-center space-y-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
          >
            <h1 className="text-5xl font-extrabold tracking-tight text-white">
              PaperPod
            </h1>
          </motion.div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-gray-400 text-base max-w-sm mx-auto leading-relaxed"
          >
            Turn any research paper into an interactive AI panel discussion
          </motion.p>
        </div>

        {/* Main Card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5 }}
          className="rounded-2xl border border-white/[0.08] bg-[#0a1120]/90 backdrop-blur-2xl shadow-2xl shadow-black/50 ring-1 ring-inset ring-white/[0.04] p-7"
        >
          <AnimatePresence mode="wait">
            {isLoading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex flex-col items-center justify-center gap-4 py-12"
              >
                <div className="relative">
                  <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-xl" />
                  <Loader2 className="relative w-10 h-10 text-blue-400 animate-spin" />
                </div>
                <p className="text-gray-300 text-sm">{loadingText}</p>
              </motion.div>
            ) : (
              <motion.div
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-5"
              >
                {/* Dropzone */}
                <div
                  {...getRootProps()}
                  className={cn(
                    "group relative flex flex-col items-center justify-center gap-4 p-10 rounded-2xl transition-all duration-300 cursor-pointer overflow-hidden",
                    "border border-dashed",
                    isDragActive
                      ? "border-blue-400 bg-blue-500/[0.08] scale-[1.01]"
                      : "border-white/[0.12] hover:border-white/[0.25] bg-white/[0.02] hover:bg-white/[0.04]"
                  )}
                >
                  {/* Hover gradient overlay */}
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-blue-500/[0.04] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

                  <input {...getInputProps()} />
                  <div className={cn(
                    "relative w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300",
                    isDragActive
                      ? "bg-blue-500/15 text-blue-400 scale-110"
                      : "bg-white/[0.05] text-gray-500 group-hover:text-gray-300 group-hover:bg-white/[0.08]"
                  )}>
                    {isDragActive ? <FileText className="w-7 h-7" /> : <Upload className="w-7 h-7" />}
                  </div>
                  <div className="text-center relative">
                    <p className="text-white font-semibold">
                      {isDragActive ? "Drop your PDF here" : "Upload a PDF"}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">Drag and drop or click to browse</p>
                  </div>
                </div>

                {/* Divider */}
                <div className="flex items-center gap-4 py-1">
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                  <span className="text-[11px] text-gray-600 uppercase tracking-widest">or</span>
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                </div>

                {/* arXiv URL */}
                <div className="flex gap-2">
                  <div className="flex-1 relative group/input">
                    <Link className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 group-focus-within/input:text-blue-400 transition-colors" />
                    <input
                      type="text"
                      placeholder="Paste an arXiv URL..."
                      value={arxivUrl}
                      onChange={(e) => setArxivUrl(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleArxivSubmit()}
                      className="w-full h-12 pl-11 pr-4 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white text-sm placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/30 focus:bg-white/[0.05] transition-all"
                    />
                  </div>
                  <button
                    onClick={handleArxivSubmit}
                    disabled={!arxivUrl.trim()}
                    className="h-12 px-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition-all hover:shadow-lg hover:shadow-blue-500/20 active:scale-[0.97] disabled:opacity-30 disabled:hover:shadow-none flex items-center gap-2"
                  >
                    Generate
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>

                {/* Options */}
                <div className="grid grid-cols-2 gap-4 pt-2">
                  {/* Level */}
                  <div className="space-y-2.5">
                    <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 pl-1">Level</label>
                    <div className="flex gap-1.5 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                      {(["beginner", "technical"] as const).map((level) => (
                        <button
                          key={level}
                          onClick={() => setDifficulty(level)}
                          className={cn(
                            "flex-1 py-2 text-xs font-medium rounded-lg transition-all duration-200",
                            difficulty === level
                              ? "bg-white/[0.1] text-white shadow-sm"
                              : "text-gray-500 hover:text-gray-300"
                          )}
                        >
                          {level.charAt(0).toUpperCase() + level.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Length */}
                  <div className="space-y-2.5">
                    <label className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-500 pl-1">Length</label>
                    <div className="flex gap-1.5 p-1 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                      {([
                        { key: "quick", label: "5m" },
                        { key: "standard", label: "10m" },
                        { key: "deep", label: "20m" },
                      ] as const).map(({ key, label }) => (
                        <button
                          key={key}
                          onClick={() => setLength(key)}
                          className={cn(
                            "flex-1 py-2 text-xs font-medium rounded-lg transition-all duration-200",
                            length === key
                              ? "bg-white/[0.1] text-white shadow-sm"
                              : "text-gray-500 hover:text-gray-300"
                          )}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Recent sessions */}
        <RecentSessions />
      </motion.div>
    </main>
  );
}

function RecentSessions() {
  const router = useRouter();
  const { data: sessions, refetch } = useQuery({
    queryKey: ["recent-sessions"],
    queryFn: getRecentSessions,
  });

  if (!sessions || sessions.length === 0) return null;

  async function handleDelete(e: React.MouseEvent, sessionId: string) {
    e.stopPropagation();
    const { deleteSession } = await import("@/lib/api");
    await deleteSession(sessionId);
    refetch();
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="space-y-3"
    >
      <h3 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-600 pl-1">
        Continue listening
      </h3>
      <div className="space-y-2">
        {sessions.map((s, i) => (
          <motion.div
            key={s.session_id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.45 + i * 0.05 }}
            onClick={() => router.push(`/session/${s.session_id}`)}
            className="group flex items-center gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.05] hover:border-white/[0.12] transition-all duration-200 cursor-pointer"
          >
            <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-500/20 transition-colors">
              <Play className="w-4 h-4 text-blue-400 ml-0.5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white font-medium truncate">{s.paper_title}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[11px] text-gray-500">
                  Turn {s.current_turn_index + 1}/{s.total_turns}
                </span>
                <span className="w-1 h-1 rounded-full bg-gray-700" />
                <span className="text-[11px] text-gray-500 capitalize">{s.difficulty}</span>
                {/* Mini progress bar */}
                <div className="w-12 h-1 rounded-full bg-white/[0.06] ml-1">
                  <div
                    className="h-full rounded-full bg-blue-500/50"
                    style={{ width: `${((s.current_turn_index + 1) / s.total_turns) * 100}%` }}
                  />
                </div>
              </div>
            </div>
            <button
              onClick={(e) => handleDelete(e, s.session_id)}
              className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all p-2 rounded-lg hover:bg-red-500/10"
              title="Delete session"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
