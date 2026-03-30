from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from deps import get_db
from models.schemas import QuizStartRequest, QuizQuestion, QuizAnswerRequest, QuizResult

router = APIRouter(tags=["quiz"])


@router.post("/quiz/{session_id}/start", response_model=QuizQuestion)
async def start_quiz(session_id: str, req: QuizStartRequest, db: Session = Depends(get_db)):
    """Start quiz mode for the current section."""
    # TODO: Phase 7 — quiz agent generates question
    return QuizQuestion(
        question_id="placeholder",
        text="Placeholder quiz question — will be implemented in Phase 7",
        section=req.section or "intro",
    )


@router.post("/quiz/{session_id}/answer", response_model=QuizResult)
async def answer_quiz(session_id: str, req: QuizAnswerRequest, db: Session = Depends(get_db)):
    """Evaluate a quiz answer."""
    # TODO: Phase 7 — evaluate with Gemini
    return QuizResult(
        correct=True,
        feedback="Placeholder feedback",
        weak_concepts=[],
    )
