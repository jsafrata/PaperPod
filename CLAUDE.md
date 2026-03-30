# Interactive Paper Podcast - Step-by-Step Build Plan

## Context

Building a hackathon MVP that turns research papers into interactive, multi-speaker podcast experiences. User uploads a PDF/arXiv link, system generates a 3-speaker discussion (Host, Expert, Skeptic) with synced visuals, live Q&A, quiz mode, and recap. Greenfield project — no code exists yet.

---

## Tech Stack Decisions

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + Framer Motion | Fast iteration, polished UI |
| Frontend hosting | Vercel | Zero-config Next.js deploys |
| Backend | FastAPI + Uvicorn + Pydantic | Python ecosystem for PDF/ML tooling |
| Backend hosting | Railway | Easy Python deploys, managed Postgres |
| Database | Supabase Postgres via SQLModel | Managed Postgres + pgvector + free tier |
| Vector search | pgvector (Supabase Postgres) | Built into Supabase, no separate service |
| Session state | In-memory Python dict (MVP), upgrade to Redis if needed | Single process for demo |
| AI — Document | Gemini 3 Flash (`gemini-3-flash-preview`) — structured output, knowledge pack | Fast, JSON mode |
| AI — TTS | Gemini 2.5 Flash TTS (`gemini-2.5-flash-tts`, Kore/Puck/Charon voices) | Pre-rendered podcast audio |
| AI — Live Q&A | Gemini 3.1 Flash Live (`gemini-3.1-flash-live-preview`) | Streaming voice I/O for interrupts |
| AI — Embeddings | text-embedding-004 (768-dim) | pgvector retrieval |
| AI — Images | Gemini 3.1 Flash Image (`gemini-3.1-flash-image-preview`) | AI explainer visuals |
| PDF parsing | PyMuPDF (fitz) + pdfplumber | Robust extraction |
| File storage | Supabase Storage | PDFs, extracted images, generated audio |
| Real-time | WebSocket (single connection per session) | Bidirectional for interrupts/quiz |

### Audio Architecture: TTS vs Live API

| Use case | API | Why |
|----------|-----|-----|
| Scripted podcast turns (20-30) | TTS (`gemini-2.5-flash-tts`) | Parallel batch, cacheable, 3 distinct voices |
| User interrupt Q&A | Live API (`gemini-3.1-flash-live-preview`) | Streaming audio, low latency, voice input |
| Quiz question/feedback | TTS | Short, pre-generated |
| Host resume bridge | Live API (streamed after answer) | Flows naturally from Q&A session |

**Live API flow:** User interrupts → text or voice sent via WebSocket → backend opens Live API session (cached per speaker) → audio chunks streamed back as base64 → frontend plays via Web Audio API (`useStreamingAudio`) → transcript deltas shown in real-time → host resume streams → podcast resumes.

**Fallback:** If Live API fails, the WebSocket handler automatically falls back to the TTS-based flow (generate text → TTS → upload → send URL).

---

## Environment Variables

### Backend (`backend/.env`)
```
GEMINI_API_KEY=                # Google AI Studio — all Gemini calls
SUPABASE_URL=                  # Supabase project URL (e.g. https://xxx.supabase.co)
SUPABASE_SERVICE_KEY=          # Supabase service role key (for storage + DB admin)
DATABASE_URL=                  # Postgres connection string (from Supabase: Settings → Database)
FRONTEND_URL=                  # Vercel deploy URL for CORS (e.g. https://your-app.vercel.app)
SECRET_KEY=                    # Random 32-char string for session signing
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_URL=           # Railway backend URL (e.g. https://your-app.railway.app)
NEXT_PUBLIC_WS_URL=            # WebSocket URL (e.g. wss://your-app.railway.app)
```

---

## Phase 1: Project Scaffolding (Hours 0-2)

### 1.1 Backend Setup
- Initialize `backend/` with FastAPI project structure
- Create `main.py` with CORS (allow `FRONTEND_URL`), lifespan, router mounting
- Create `config.py` with pydantic-settings loading from `.env` (GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, DATABASE_URL, FRONTEND_URL, SECRET_KEY)
- Set up SQLModel + Supabase Postgres (`models/db.py`) using `DATABASE_URL`
- Enable pgvector extension for embeddings: `CREATE EXTENSION IF NOT EXISTS vector`
- Tables: `Paper`, `Section`, `Visual`, `Chunk` (with vector column), `Session`, `PodcastTurn`, `QAEntry`, `QuizAttempt`
- Create `requirements.txt`: fastapi, uvicorn, sqlmodel, psycopg2-binary, pgvector, google-genai, pymupdf, pdfplumber, pillow, numpy, python-multipart, websockets, supabase, python-dotenv
- Create `backend/.env.example` with all required vars documented
- Create `storage/supabase.py` for file upload/download via Supabase Storage SDK
- Set up Supabase Storage buckets: `papers`, `visuals`, `audio`

**Files to create:**
```
backend/
├── main.py
├── config.py
├── deps.py
├── .env.example
├── models/
│   ├── __init__.py
│   ├── db.py          # SQLModel table definitions (Postgres + pgvector)
│   ├── schemas.py     # Pydantic request/response schemas
│   └── enums.py       # SessionMode, SpeakerRole, VisualType
├── routers/__init__.py
├── services/__init__.py
├── agents/__init__.py
├── prompts/__init__.py
├── storage/
│   └── supabase.py    # Supabase Storage client (upload/download/get_url)
└── requirements.txt
```

### 1.2 Frontend Setup
- `npx create-next-app@latest frontend --typescript --tailwind --app --src-dir`
- Install deps: `zustand framer-motion lucide-react react-dropzone @tanstack/react-query clsx tailwind-merge sonner`
- Configure dark theme in `tailwind.config.ts` and `globals.css`
- Create speaker color tokens: Host=blue, Expert=green, Skeptic=amber
- Build primitive components: `Button`, `Card`, `Badge`, `Progress`
- Create all page shells (empty) for upload, processing, listening, quiz, recap

**Files to create:**
```
frontend/src/
├── app/
│   ├── layout.tsx              # Dark theme, fonts, QueryClientProvider
│   ├── page.tsx                # Upload page
│   └── session/[id]/
│       ├── page.tsx            # Listening experience
│       ├── processing/page.tsx
│       └── recap/page.tsx
├── components/ui/              # Button, Card, Badge
├── stores/
│   ├── sessionStore.ts
│   └── playbackStore.ts
├── lib/
│   ├── api.ts                  # Typed fetch wrappers
│   ├── types.ts                # Shared interfaces (Turn, Visual, Session, etc.)
│   └── constants.ts            # Speaker colors, role labels
└── public/speakers/            # 3 pre-designed speaker portraits
```

### 1.3 Verify
- `uvicorn main:app --reload` serves API at localhost:8000
- `npm run dev` serves frontend at localhost:3000
- Both run simultaneously without conflict
- Backend connects to Supabase Postgres (test with a simple query)
- Supabase Storage buckets created and accessible

---

## Phase 2: Paper Upload & Ingestion Pipeline (Hours 2-6)

### 2.1 Upload Endpoints
- `POST /api/papers/upload` — accepts PDF multipart upload, saves to Supabase Storage `papers/{uuid}.pdf`
- `POST /api/papers/arxiv` — accepts `{ arxiv_url }`, downloads PDF, uploads to Supabase Storage
- `GET /api/papers/{id}/status` — returns processing step statuses for polling

**Files:** `backend/routers/papers.py`, `backend/utils/arxiv.py`

### 2.2 PDF Parsing Service
- Extract text blocks per page via PyMuPDF
- Detect section headers (bold/large font, numbered patterns like "1. Introduction")
- Fallback: send full text to Gemini to return section boundaries
- Store sections in `Section` table

**File:** `backend/services/paper_ingestion.py`

### 2.3 Figure Extraction
- PyMuPDF `page.get_images()` to extract embedded images
- Caption detection: regex for `Figure|Fig\.|Table` in nearby text blocks
- Save images as PNG to Supabase Storage `visuals/{paper_id}/{visual_id}.png`
- Store metadata in `Visual` table with section association and Supabase public URL

**File:** `backend/services/paper_ingestion.py` (same file, separate functions)

### 2.4 Frontend Upload Flow
- Build `UploadZone` component with react-dropzone (drag-and-drop + click)
- Build `ArxivInput` component (text field with URL validation)
- Build `UploadOptions` (beginner/technical toggle, focus area selector)
- On submit: POST to backend, receive `paper_id`, redirect to processing page

**Files:** `frontend/src/components/upload/UploadZone.tsx`, `ArxivInput.tsx`, `UploadOptions.tsx`

### 2.5 Processing Status Page
- Poll `GET /api/papers/{id}/status` every 2 seconds
- Display 5 steps with animated checkmarks: Reading paper, Extracting visuals, Building explanations, Generating voices, Preparing quiz
- Auto-navigate to listening page on completion

**Files:** `frontend/src/app/session/[id]/processing/page.tsx`, `frontend/src/components/processing/ProcessingSteps.tsx`

### 2.6 Verify
- Upload a real PDF, confirm it parses into sections and extracts figures
- arXiv link downloads and processes correctly
- Processing page shows real progress

---

## Phase 3: Knowledge Pack & Retrieval (Hours 6-10)

### 3.1 Text Chunking + Embeddings
- Chunk paper text: ~300-400 tokens per chunk, 50-token overlap, section-aware
- Figure captions as separate mini-chunks tagged with `visual_id`
- Generate embeddings via Gemini `text-embedding-004`
- Store embeddings in Postgres via pgvector (`Chunk` table has `embedding vector(768)` column)

**Files:** `backend/services/chunker.py`, `backend/services/retrieval.py`

### 3.2 Knowledge Pack Generation
- Upload PDF to Gemini Files API
- Single large structured-output call returning:
  - `title, authors, one_sentence_summary`
  - `sections[]` with key_points
  - `core_claims[], methods[], results[], limitations[]`
  - `glossary[]` (term, definition, analogy)
  - `likely_questions[]` (5-10)
  - `quiz_bank[]` (10-15 questions with answers)
  - `figure_descriptions[]`
- Store as JSON blob in Paper record

**Files:** `backend/services/knowledge_pack.py`, `backend/prompts/knowledge_pack.py`

### 3.3 Retrieval Service
- `RetrievalService` class with `store_embeddings()` and `search(query, top_k=5)`
- Uses pgvector `<=>` cosine distance operator for similarity search
- SQL: `SELECT * FROM chunk WHERE paper_id = :pid ORDER BY embedding <=> :query_vec LIMIT :k`
- Returns ranked chunks with section and visual references

**File:** `backend/services/retrieval.py`

### 3.4 Verify
- Process a paper end-to-end, inspect knowledge pack JSON
- Query retrieval with sample questions, confirm relevant chunks returned

---

## Phase 4: Podcast Script + TTS + Playback (Hours 10-16)

### 4.1 Script Generation
- Gemini structured output call using knowledge pack as context
- Generate 20-30 turns following this arc:
  1. Host: Welcome, paper title, why it matters (2 turns)
  2. Expert: Core contribution (2 turns)
  3. Skeptic: Initial reaction (1 turn)
  4. Host→Expert→Skeptic: Methods discussion with figure refs (4-5 turns)
  5. Host→Expert→Skeptic: Results discussion with figure refs (4-5 turns)
  6. Host→Skeptic→Expert: Limitations (3-4 turns)
  7. Host: Wrap-up, invite questions (1-2 turns)
- Each turn: `{ speaker, section, text (2-4 sentences), visual_id?, notes }`

**Files:** `backend/services/script_generator.py`, `backend/prompts/script.py`

### 4.2 TTS Generation
- Speaker voice config: Host=Kore, Expert=Puck, Skeptic=Charon (Gemini TTS voices)
- Generate audio for all turns in parallel via `asyncio.gather` (biggest latency win)
- Upload audio to Supabase Storage `audio/{session_id}/{turn_index}.wav`
- Store public URL in `PodcastTurn.audio_url`
- Semaphore for rate limiting (max 5 concurrent)

**File:** `backend/services/tts.py`

### 4.3 Session Creation
- `POST /api/sessions` — creates session, triggers script + TTS generation (or uses pre-generated)
- `GET /api/podcast/{session_id}/turns` — returns all turns with Supabase audio URLs (frontend fetches directly from Supabase CDN)
- No need for `GET /api/audio/{audio_id}` — Supabase Storage serves files directly via public URLs

**Files:** `backend/routers/sessions.py`, `backend/routers/podcast.py`

### 4.4 Frontend Audio Player
- `useAudioPlayer` hook: manages single HTMLAudioElement
- Sequential turn playback: load turn → play → on 'ended' → next turn
- Update `playbackStore` (currentTurnIndex, activeSpeaker, isPlaying)
- Prefetch next turn's audio in background for gapless transitions

**File:** `frontend/src/hooks/useAudioPlayer.ts`

### 4.5 Frontend Listening Layout
- `SpeakerPanel` with 3 `SpeakerCard` components
  - Active speaker: scale 1.05, colored ring/glow, pulse animation
  - Inactive: 60% opacity
- `TranscriptPanel`: scrolling list of `TranscriptLine` components
  - Current line: left-border accent color + bold
  - Auto-scroll via `scrollIntoView({ behavior: 'smooth' })`
- `SectionProgress` bar: Intro | Method | Results | Limitations
- `ControlBar`: play/pause, section indicator

**Files:**
```
frontend/src/components/listening/
├── ListeningLayout.tsx
├── SpeakerPanel.tsx
├── SpeakerCard.tsx
├── TranscriptPanel.tsx
├── TranscriptLine.tsx
├── ControlBar.tsx
└── SectionProgress.tsx
```

### 4.6 Verify
- Upload paper → processing completes → listening page loads
- Audio plays sequentially through all turns
- Speaker cards animate on turn changes
- Transcript scrolls and highlights correctly

---

## Phase 5: Visual Sync (Hours 16-18)

### 5.1 Visual Mapping
- During script generation, each turn with a figure reference gets a `visual_id`
- `GET /api/visuals/{paper_id}` returns all extracted visuals with metadata
- Frontend fetches visuals on session load

**File:** `backend/services/visual_mapper.py`

### 5.2 Visual Panel
- `VisualPanel` component displays image for current turn's `visual_id`
- `AnimatePresence` crossfade between visuals
- `VisualBadge` pill: "From paper" (gray) or "AI explainer" (purple)
- Caption text below image
- Fallback: paper title card when no visual mapped

**Files:** `frontend/src/components/listening/VisualPanel.tsx`, `VisualBadge.tsx`

### 5.3 Verify
- During playback, figures appear at correct moments
- Transitions are smooth, provenance badges display correctly

---

## Phase 6: Live Interruption & Q&A (Hours 18-24)

### 6.1 Agent System
- `Orchestrator` class: routes to Host/Expert/Skeptic based on question intent
- Simple keyword routing (no LLM call needed):
  - "limitation/trust/valid/weak/flaw/bias" → Skeptic
  - "quiz/test me" → Quiz flow
  - Everything else → Expert (safe default)
- Each speaker agent: system prompt + knowledge pack context + recent history → Gemini call
- `RetrievalAgent`: fetches relevant chunks before speaker generates response

**Files:**
```
backend/agents/
├── orchestrator.py
├── host.py
├── expert.py
├── skeptic.py
└── retrieval_agent.py
backend/prompts/
├── host.py
├── expert.py
└── skeptic.py
```

### 6.2 WebSocket Endpoint
- `WS /api/ws/{session_id}` — single bidirectional connection
- Client messages: `interrupt`, `quiz_start`, `quiz_answer`, `simplify`, `go_deeper`
- Server messages: `answer`, `resume`, `quiz_question`, `quiz_feedback`, `visual_update`
- On interrupt: retrieve chunks → route to agent → generate response → TTS → send back → Host generates bridge line → resume

**File:** `backend/routers/interact.py`

### 6.3 Frontend Interrupt Flow
- `InterruptButton` + expandable `TextInterruptInput` in ControlBar
- `useInterrupt` hook:
  1. Pause audio immediately
  2. Save resume point (turn index + currentTime)
  3. Set mode = 'interrupted'
  4. Send question over WebSocket
  5. Receive answer turn(s), play them
  6. Receive resume signal, continue from saved point
- `QuickActions`: Simplify, Go deeper, Quiz me, Why? — each sends a preset message

**Files:** `frontend/src/hooks/useInterrupt.ts`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/components/listening/InterruptButton.tsx`, `QuickActions.tsx`

### 6.4 Verify
- Click interrupt → audio stops → type question → answer plays → podcast resumes
- Quick actions work (Simplify, Go deeper)
- Multiple interruptions in a row work correctly

---

## Phase 7: Quiz Mode (Hours 24-30)

### 7.1 Quiz Engine
- `QuizAgent`: selects questions from knowledge pack quiz bank based on current section
- Adapts: prioritizes weak concepts, avoids repeats
- Evaluates free-text answers via Gemini (correct/incorrect + explanation)
- Tracks weak concepts in session state

**Files:** `backend/agents/quiz_agent.py`, `backend/services/quiz_engine.py`, `backend/prompts/quiz.py`

### 7.2 Frontend Quiz UI
- Quiz overlay on listening page (not a separate route)
- `QuizCard`: question text, text input, submit button
- `QuizFeedback`: correct/incorrect indicator, explanation, weak concepts
- "Next question" or "Back to podcast" actions
- Host voice asks the question (TTS), Expert voice gives feedback

**Files:** `frontend/src/components/quiz/QuizCard.tsx`, `QuizInput.tsx`, `QuizFeedback.tsx`, `frontend/src/hooks/useQuiz.ts`

### 7.3 Verify
- Click "Quiz me" → question appears → submit answer → feedback shows → can continue or return to podcast

---

## Phase 8: AI Explainer Visuals (Hours 30-33)

### 8.1 Visual Generation
- `VisualAgent`: decides when a simpler diagram would help
- Uses Gemini image generation to create: simplified architecture diagrams, flowcharts, comparison cards
- Triggered by user request ("Explain this figure") or "Simplify" quick action
- Clearly labeled "AI explainer visual"

**Files:** `backend/agents/visual_agent.py`, `backend/services/visual_generator.py`

### 8.2 Verify
- Request a simpler visual → AI-generated image appears with correct badge

---

## Phase 9: Recap & Session End (Hours 33-36)

### 9.1 Recap Generation
- `GET /api/recap/{session_id}` triggers Gemini call using:
  - Knowledge pack, session transcript, Q&A history, quiz results, weak concepts
- Returns: 3 takeaways, 2 limitations, 3 flashcards, weak concepts list

**Files:** `backend/services/recap_generator.py`, `backend/routers/recap.py`, `backend/prompts/recap.py`

### 9.2 Frontend Recap Page
- `TakeawaysList`: numbered key takeaways
- `FlashcardDeck`: flip-card carousel
- `WeakConceptsList`: areas to review
- "Replay" and "Download transcript" buttons

**Files:** `frontend/src/app/session/[id]/recap/page.tsx`, `frontend/src/components/recap/TakeawaysList.tsx`, `FlashcardDeck.tsx`, `WeakConceptsList.tsx`

### 9.3 Verify
- End session → recap page shows meaningful takeaways, flashcards, weak concepts

---

## Phase 10: Polish & Demo Hardening (Hours 36-42)

### 10.1 Pre-compute Demo Paper
- Pick one well-formatted arXiv paper (e.g., "Attention Is All You Need" or a recent notable paper)
- Run full pipeline, cache: knowledge pack, script, all audio files, extracted figures
- On demo, load cached data for instant start

### 10.2 UI Polish
- Smooth all Framer Motion transitions (speaker switches, visual crossfades, quiz entrance)
- Add loading skeletons where needed
- Improve spacing, typography hierarchy
- Ensure dark theme is consistent everywhere
- Add subtle ambient audio or UI sounds for state changes

### 10.3 Latency Optimization
- Parallel TTS generation (already in plan)
- Prefetch next 2 turns' audio during playback
- Cache Gemini responses where possible

### 10.4 Error Handling
- Graceful fallbacks for failed TTS (show text only)
- WebSocket reconnection logic
- Processing timeout handling with user-friendly message

### 10.5 Demo Rehearsal
- Run the full demo script (PRD Section 24) end-to-end
- Time each transition, identify any jank
- Have backup plan if live Gemini calls are slow (use cached responses)

---

## Cut Order (If Time Gets Tight)

1. Voice interruption (keep text only)
2. AI-generated explainer visuals (keep original paper visuals only)
3. Voice answers in quiz (keep text only)
4. Advanced recap personalization (keep simple recap)
5. Multiple focus areas (hardcode "overview" mode)

---

## Key API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/papers/upload` | PDF upload → Supabase Storage |
| POST | `/api/papers/arxiv` | arXiv URL input → Supabase Storage |
| GET | `/api/papers/{id}/status` | Processing progress |
| POST | `/api/sessions` | Create session |
| GET | `/api/sessions/{id}` | Session metadata |
| GET | `/api/podcast/{session_id}/turns` | All turns with Supabase audio URLs |
| GET | `/api/visuals/{paper_id}` | All visuals with Supabase image URLs |
| WS | `/api/ws/{session_id}` | Real-time interaction |
| GET | `/api/recap/{session_id}` | Session recap |

Audio and image files are served directly from Supabase Storage CDN — no backend proxy needed.

---

## Deployment

### Frontend (Vercel)
- Connect GitHub repo → Vercel auto-deploys `frontend/` directory
- Set env vars: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`
- Root directory: `frontend`

### Backend (Railway)
- Connect GitHub repo → Railway deploys `backend/` directory
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set env vars: `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`, `FRONTEND_URL`, `SECRET_KEY`
- Root directory: `backend`

### Supabase
- Create project → get URL + service key
- Database: Postgres with pgvector extension enabled
- Storage: Create 3 public buckets: `papers`, `visuals`, `audio`
- Connection string from: Settings → Database → Connection string (URI)

### Supabase Storage Buckets

| Bucket | Contents | Access |
|--------|----------|--------|
| `papers` | Uploaded PDFs | Private (backend only) |
| `visuals` | Extracted figures, AI-generated visuals | Public (frontend reads directly) |
| `audio` | TTS audio files per turn | Public (frontend plays directly) |
