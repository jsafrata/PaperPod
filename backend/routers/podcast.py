from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from deps import get_db
from models.schemas import PodcastTurnsResponse, TurnResponse
from models.db import PodcastTurn, Session as SessionModel

router = APIRouter(tags=["podcast"])


@router.get("/podcast/{session_id}/turns", response_model=PodcastTurnsResponse)
async def get_podcast_turns(session_id: str, db: Session = Depends(get_db)):
    """Get all podcast turns for a session."""
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    turns = db.exec(
        select(PodcastTurn)
        .where(PodcastTurn.session_id == session_id)
        .order_by(PodcastTurn.turn_index)
    ).all()

    return PodcastTurnsResponse(
        session_id=session_id,
        turns=[
            TurnResponse(
                index=t.turn_index,
                speaker=t.speaker,
                text=t.text,
                audio_url=t.audio_url,
                visual_id=t.visual_id,
                section=t.section,
            )
            for t in turns
        ],
    )
