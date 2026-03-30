"""Recap generation — takeaways, flashcards, weak concepts."""

import asyncio
import json
import logging
from typing import Optional

from google import genai
from google.genai import types
from sqlmodel import Session, select

from config import settings
from models.db import Paper, PodcastTurn, QAEntry, QuizAttempt, Session as SessionModel
from prompts.recap import RECAP_SYSTEM_PROMPT, RECAP_USER_PROMPT, RECAP_BEGINNER_INSTRUCTION, RECAP_TECHNICAL_INSTRUCTION

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"


async def generate_recap(session_id: str, db: Session, up_to_turn: Optional[int] = None) -> dict:
    """Generate a session recap using Gemini."""
    session = db.get(SessionModel, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    paper = db.get(Paper, session.paper_id)
    if not paper:
        raise ValueError("Paper not found")

    knowledge_pack = json.loads(paper.knowledge_pack_json) if paper.knowledge_pack_json else {}

    # Get turns the user actually heard
    turn_query = select(PodcastTurn).where(PodcastTurn.session_id == session_id)
    if up_to_turn is not None:
        turn_query = turn_query.where(PodcastTurn.turn_index <= up_to_turn)
    turn_query = turn_query.order_by(PodcastTurn.turn_index)
    turns_heard = db.exec(turn_query).all()

    turns_text = "\n".join(
        f"[{t.speaker}] ({t.section}): {t.text}"
        for t in turns_heard
    ) or "No turns heard yet."

    # Gather Q&A history
    qas = db.exec(
        select(QAEntry)
        .where(QAEntry.session_id == session_id)
        .order_by(QAEntry.created_at)
    ).all()
    qa_text = "\n".join(
        f"Q: {qa.question}\nA ({qa.speaker}): {qa.answer}"
        for qa in qas
    ) or "No questions asked."

    # Gather quiz results
    attempts = db.exec(
        select(QuizAttempt)
        .where(QuizAttempt.session_id == session_id)
        .order_by(QuizAttempt.created_at)
    ).all()

    quiz_text = "\n".join(
        f"Q: {a.question_text} | Answer: {a.user_answer} | {'Correct' if a.correct else 'Wrong'} | Concept: {a.concept}"
        for a in attempts
    ) or "No quiz attempts."

    # Weak concepts
    weak = json.loads(session.weak_concepts_json) if session.weak_concepts_json else []
    wrong_concepts = list(set(a.concept for a in attempts if not a.correct))
    all_weak = list(set(weak + wrong_concepts))

    # Build summary from what was actually discussed
    kp_summary = f"""Paper: {knowledge_pack.get("title", "")}

Content the user heard ({len(turns_heard)} turns):
{turns_text}"""

    # Generate recap
    client = genai.Client(api_key=settings.gemini_api_key)

    difficulty = session.difficulty or "beginner"
    difficulty_instruction = RECAP_BEGINNER_INSTRUCTION if difficulty == "beginner" else RECAP_TECHNICAL_INSTRUCTION

    prompt = RECAP_USER_PROMPT.format(
        knowledge_pack_summary=kp_summary,
        qa_history=qa_text,
        quiz_results=quiz_text,
        weak_concepts=", ".join(all_weak) if all_weak else "None identified",
        difficulty_instruction=difficulty_instruction,
    )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        )],
        config=types.GenerateContentConfig(
            system_instruction=RECAP_SYSTEM_PROMPT,
            temperature=0.4,
            response_mime_type="application/json",
        ),
    ))

    recap = json.loads(response.text.strip())

    # Ensure all fields exist
    recap.setdefault("takeaways", [])
    recap.setdefault("limitations", [])
    recap.setdefault("flashcards", [])
    recap.setdefault("weak_concepts", all_weak)

    return recap
