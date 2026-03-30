import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from deps import get_db
from models.schemas import RecapResponse
from models.db import Session as SessionModel
from services.recap_generator import generate_recap

logger = logging.getLogger(__name__)

router = APIRouter(tags=["recap"])


@router.get("/recap/{session_id}", response_model=RecapResponse)
async def get_recap(session_id: str, turn_index: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Generate and return session recap for content heard so far."""
    session = db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        recap = await generate_recap(session_id, db, up_to_turn=turn_index)
        return RecapResponse(
            takeaways=recap.get("takeaways", []),
            limitations=recap.get("limitations", []),
            flashcards=[
                {"front": f.get("front", ""), "back": f.get("back", "")}
                for f in recap.get("flashcards", [])
            ],
            weak_concepts=recap.get("weak_concepts", []),
        )
    except Exception as e:
        logger.error(f"Recap generation failed: {e}", exc_info=True)
        # Fallback to basic recap from knowledge pack
        from models.db import Paper
        import json
        paper = db.get(Paper, session.paper_id)
        kp = json.loads(paper.knowledge_pack_json) if paper and paper.knowledge_pack_json else {}
        return RecapResponse(
            takeaways=kp.get("core_claims", ["No takeaways available"])[:3],
            limitations=kp.get("limitations", ["No limitations identified"])[:2],
            flashcards=[],
            weak_concepts=json.loads(session.weak_concepts_json) if session.weak_concepts_json else [],
        )
