import { API_URL } from "./constants";
import type { PaperStatus, SessionData, Turn, Visual, RecapData } from "./types";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

/** Resolve a URL that may be relative (e.g. /api/storage/...) to an absolute URL. */
export function resolveUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  // Relative URL from backend — prepend API_URL
  return `${API_URL}${url}`;
}

// --- Papers ---

export async function uploadPaper(file: File): Promise<{ paper_id: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/api/papers/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function submitArxiv(arxivUrl: string, difficulty = "beginner", length = "standard"): Promise<{ paper_id: string; status: string }> {
  return fetchJSON("/api/papers/arxiv", {
    method: "POST",
    body: JSON.stringify({ arxiv_url: arxivUrl, difficulty, length }),
  });
}

export async function getPaperStatus(paperId: string): Promise<PaperStatus> {
  return fetchJSON(`/api/papers/${paperId}/status`);
}

// --- Sessions ---

export async function createSession(paperId: string, difficulty = "beginner", focus?: string): Promise<SessionData> {
  return fetchJSON("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ paper_id: paperId, difficulty, focus }),
  });
}

export async function getSession(sessionId: string): Promise<SessionData> {
  return fetchJSON(`/api/sessions/${sessionId}`);
}

export async function saveProgress(sessionId: string, turnIndex: number): Promise<void> {
  await fetchJSON(`/api/sessions/${sessionId}/save-turn?turn_index=${turnIndex}`, {
    method: "POST",
  });
}

export async function getRecentSessions(): Promise<Array<{
  session_id: string;
  paper_title: string;
  current_turn_index: number;
  total_turns: number;
  difficulty: string;
  created_at: string;
}>> {
  return fetchJSON("/api/sessions/recent/list");
}

export async function deleteSession(sessionId: string): Promise<void> {
  await fetchJSON(`/api/sessions/${sessionId}`, { method: "DELETE" });
}

// --- Podcast ---

export async function getPodcastTurns(sessionId: string): Promise<{ session_id: string; turns: Turn[] }> {
  const data = await fetchJSON<{ session_id: string; turns: Turn[] }>(`/api/podcast/${sessionId}/turns`);
  // Resolve relative audio URLs to absolute so browser can load them
  data.turns = data.turns.map((t) => ({
    ...t,
    audio_url: resolveUrl(t.audio_url),
  }));
  return data;
}

// --- Visuals ---

export async function getVisuals(paperId: string): Promise<Visual[]> {
  const data = await fetchJSON<Visual[]>(`/api/visuals/${paperId}`);
  return data.map((v) => ({ ...v, image_url: resolveUrl(v.image_url) || v.image_url }));
}

// --- Recap ---

export async function getRecap(sessionId: string, turnIndex?: number): Promise<RecapData> {
  const params = turnIndex !== undefined ? `?turn_index=${turnIndex}` : "";
  return fetchJSON(`/api/recap/${sessionId}${params}`);
}
