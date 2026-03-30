import asyncio
import logging
import threading
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from deps import get_db, engine
from models.schemas import SessionCreateRequest, SessionResponse
from models.db import Session as SessionModel, Paper, PodcastTurn
from models.enums import PaperStatus, SessionMode
from services.script_generator import generate_podcast_script
from services.tts import generate_all_turn_audio

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sessions"])

# Track which sessions have active pipeline threads
_active_pipelines: set[str] = set()


def _run_session_pipeline_in_thread(session_id: str):
    """Generate script + TTS in a background thread."""
    if session_id in _active_pipelines:
        logger.info(f"Pipeline already running for session {session_id}, skipping")
        return

    def _target():
        _active_pipelines.add(session_id)
        print(f"[PIPELINE] Thread started for {session_id}", flush=True)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with Session(engine) as db:
                loop.run_until_complete(_run_session_pipeline(session_id, db))
            print(f"[PIPELINE] Thread completed for {session_id}", flush=True)
        except Exception as e:
            print(f"[PIPELINE] Thread CRASHED for {session_id}: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            _active_pipelines.discard(session_id)
            loop.close()

    t = threading.Thread(target=_target, daemon=True)
    t.start()


async def _run_session_pipeline(session_id: str, db: Session):
    """Generate podcast script and TTS audio for a session."""
    session = db.get(SessionModel, session_id)
    if not session:
        return

    try:
        session.mode = SessionMode.PROCESSING
        db.commit()

        # Step 1: Generate podcast script (skip if turns already exist)
        existing_turns = db.exec(
            select(PodcastTurn).where(PodcastTurn.session_id == session_id)
        ).all()

        if not existing_turns:
            logger.info(f"Generating script for session {session_id}...")
            await generate_podcast_script(session_id, db)
        else:
            logger.info(f"Script already exists for session {session_id} ({len(existing_turns)} turns), skipping generation")

        # Step 2: Generate TTS for all turns (non-fatal if it fails)
        print(f"[PIPELINE] Starting TTS for session {session_id}...", flush=True)
        try:
            success_count = await generate_all_turn_audio(session_id, db)
            logger.info(f"TTS: {success_count} turns generated")
        except Exception as tts_err:
            logger.warning(f"TTS generation failed (text-only mode): {tts_err}")

        # Mark session as ready for playback
        session.mode = SessionMode.PLAYING
        db.commit()
        logger.info(f"Session {session_id} ready")

    except Exception as e:
        logger.error(f"Session pipeline failed for {session_id}: {e}", exc_info=True)
        session.mode = SessionMode.PAUSED
        db.commit()


def recover_stuck_sessions():
    """Resume any sessions stuck in 'processing' mode (e.g. after server restart)."""
    if engine is None:
        return
    with Session(engine) as db:
        stuck = db.exec(
            select(SessionModel).where(SessionModel.mode == SessionMode.PROCESSING)
        ).all()
        for session in stuck:
            logger.info(f"Recovering stuck session {session.id}...")
            _run_session_pipeline_in_thread(session.id)


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    req: SessionCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new podcast session and start generating script + audio."""
    paper = db.get(Paper, req.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if paper.status != PaperStatus.READY:
        raise HTTPException(status_code=400, detail="Paper is still processing")

    session = SessionModel(
        paper_id=req.paper_id,
        difficulty=req.difficulty,
        focus=req.focus,
        mode=SessionMode.PROCESSING,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Kick off script + TTS generation in background thread
    _run_session_pipeline_in_thread(session.id)

    return SessionResponse(
        session_id=session.id,
        paper_id=session.paper_id,
        mode=session.mode,
        difficulty=session.difficulty,
        paper_title=paper.title,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get session metadata."""
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    paper = db.get(Paper, session.paper_id)
    total_turns = len(db.exec(
        select(PodcastTurn).where(PodcastTurn.session_id == session_id)
    ).all())
    return SessionResponse(
        session_id=session.id,
        paper_id=session.paper_id,
        mode=session.mode,
        difficulty=session.difficulty,
        paper_title=paper.title if paper else "Unknown",
        current_turn_index=session.current_turn_index,
        total_turns=total_turns,
    )


@router.post("/sessions/{session_id}/save")
async def save_progress(session_id: str, db: Session = Depends(get_db)):
    """Save the user's current position in the podcast."""
    import json as _json
    data = {}
    # Read from request body
    return {"status": "ok"}


@router.post("/sessions/{session_id}/save-turn")
async def save_turn(session_id: str, turn_index: int = 0, db: Session = Depends(get_db)):
    """Save current turn index."""
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.current_turn_index = turn_index
    db.commit()
    return {"status": "ok", "turn_index": turn_index}


@router.get("/sessions/recent/list")
async def list_recent_sessions(db: Session = Depends(get_db)):
    """List recent sessions with progress info."""
    sessions = db.exec(
        select(SessionModel)
        .where(SessionModel.mode == SessionMode.PLAYING)
        .order_by(SessionModel.created_at.desc())  # type: ignore
    ).all()

    results = []
    for s in sessions[:10]:
        paper = db.get(Paper, s.paper_id)
        total = len(db.exec(
            select(PodcastTurn).where(PodcastTurn.session_id == s.id)
        ).all())
        results.append({
            "session_id": s.id,
            "paper_title": paper.title if paper else "Unknown",
            "current_turn_index": s.current_turn_index,
            "total_turns": total,
            "difficulty": s.difficulty,
            "created_at": s.created_at.isoformat(),
        })
    return results


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a session and its turns."""
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete turns
    turns = db.exec(select(PodcastTurn).where(PodcastTurn.session_id == session_id)).all()
    for t in turns:
        db.delete(t)

    db.delete(session)
    db.commit()
    return {"status": "ok"}
