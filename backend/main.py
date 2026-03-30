import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from deps import init_db
from storage.supabase import ensure_buckets, LOCAL_STORAGE_ROOT

from routers import papers, sessions, podcast, interact, quiz, visuals, recap
from routers.sessions import recover_stuck_sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    try:
        ensure_buckets()
    except Exception as e:
        print(f"WARNING: Could not initialize Supabase buckets: {e}")

    # Mount local storage for serving files (after ensure_buckets creates dirs)
    if os.path.isdir(LOCAL_STORAGE_ROOT):
        app.mount("/api/storage", StaticFiles(directory=LOCAL_STORAGE_ROOT), name="local-storage")

    # Recover any sessions stuck in 'processing' from a previous crash/restart
    recover_stuck_sessions()

    yield
    # Shutdown (nothing to clean up)


app = FastAPI(
    title="Interactive Paper Podcast",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001", "https://paper-pod.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(podcast.router, prefix="/api")
app.include_router(interact.router, prefix="/api")
app.include_router(quiz.router, prefix="/api")
app.include_router(visuals.router, prefix="/api")
app.include_router(recap.router, prefix="/api")



# Note: local storage mount moved into lifespan() so it runs after ensure_buckets()


@app.get("/api/health")
async def health():
    return {"status": "ok"}
