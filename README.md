# PaperPod

Turn any research paper into an interactive, multi-speaker podcast experience.

Research papers are often inaccessible — jargon-heavy for non-technical readers and difficult to parse outside your own field. PaperPod transforms them into engaging audio discussions you can listen to, interrupt, and learn from.

## How It Works

1. **Upload** a PDF or paste an arXiv link
2. **Listen** to a generated podcast with three AI speakers:
   - **Host** — frames the discussion and keeps it moving
   - **Expert** — explains methods, findings, and significance
   - **Skeptic** — challenges assumptions and highlights limitations
3. **Interact** — pause anytime to ask questions, request simpler explanations, or go deeper
4. **Quiz** — test your understanding with adaptive questions
5. **Recap** — get key takeaways, flashcards, and areas to review

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Uvicorn, Pydantic |
| Database | SQLite (local dev), Supabase Postgres (production) |
| Vector Search | pgvector |
| AI | Gemini 3 Flash (document analysis), Gemini 2.5 Flash TTS (voices), Gemini 3.1 Flash Live (Q&A) |
| PDF Parsing | PyMuPDF, pdfplumber |
| Real-time | WebSocket |

## Project Structure

```
backend/
├── agents/          # Host, Expert, Skeptic, Quiz, Retrieval agents
├── models/          # SQLModel tables + Pydantic schemas
├── prompts/         # System prompts for each agent
├── routers/         # API endpoints (papers, sessions, podcast, quiz, recap)
├── services/        # Core logic (ingestion, TTS, script gen, retrieval)
└── storage/         # File storage abstraction

frontend/src/
├── app/             # Next.js pages (upload, processing, session, recap)
├── components/      # UI components (speakers, transcript, quiz, controls)
├── hooks/           # Audio player, WebSocket, streaming audio, microphone
├── stores/          # Zustand state (session, playback)
└── lib/             # API client, types, constants
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com/apikey)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The backend runs at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `SUPABASE_URL` | Supabase project URL (production only) |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (production only) |
| `DATABASE_URL` | Postgres connection string (production only) |
| `FRONTEND_URL` | Frontend URL for CORS |
| `SECRET_KEY` | Random 32-char string for session signing |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_WS_URL` | Backend WebSocket URL |

## Deployment

- **Frontend**: Vercel (root directory: `frontend`)
- **Backend**: Railway (start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`)
- **Database**: Supabase Postgres with pgvector extension

## Built With

Built at the DeepMind Hackathon, March 2026.
