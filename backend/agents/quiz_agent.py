"""Quiz agent — dynamic question generation informed by session context."""

import logging
from typing import Optional
from sqlmodel import Session, select

from models.db import PodcastTurn, QAEntry
from services.quiz_engine import QuizEngine
from services.tts import generate_turn_audio

logger = logging.getLogger(__name__)


class QuizAgent:
    """Manages quiz interactions with context-aware question generation."""

    def __init__(self, session_id: str, db: Session):
        self.session_id = session_id
        self.db = db
        self.engine = QuizEngine(session_id, db)
        self._current_question: Optional[dict] = None

    def _gather_conversation_history(self, up_to_turn: int = 999) -> str:
        """Build a text summary of turns the user has heard so far."""
        turns = self.db.exec(
            select(PodcastTurn)
            .where(PodcastTurn.session_id == self.session_id)
            .where(PodcastTurn.turn_index <= up_to_turn)
            .order_by(PodcastTurn.turn_index)
        ).all()

        qas = self.db.exec(
            select(QAEntry)
            .where(QAEntry.session_id == self.session_id)
            .order_by(QAEntry.created_at)
        ).all()

        parts = []
        for t in turns:
            parts.append(f"[{t.speaker}]: {t.text}")
        for qa in qas[-5:]:
            parts.append(f"[User asked]: {qa.question}")
            parts.append(f"[{qa.speaker} answered]: {qa.answer}")

        return "\n".join(parts) if parts else "No conversation yet."

    async def start_quiz(self, section: Optional[str] = None, current_turn_index: int = 999) -> Optional[dict]:
        """Generate a contextual quiz question based on content heard so far."""
        conversation = self._gather_conversation_history(up_to_turn=current_turn_index)

        question = await self.engine.generate_question(
            section=section,
            conversation_history=conversation,
        )

        if not question:
            return None

        self._current_question = question

        # Skip TTS — question shown as text in overlay
        return {
            "question_id": question["question_id"],
            "text": question["text"],
            "section": question["section"],
            "audio_url": None,
        }

    async def evaluate(self, question_id: str, user_answer: str) -> dict:
        """Evaluate the user's answer and generate TTS feedback."""
        if not self._current_question or self._current_question["question_id"] != question_id:
            return {
                "correct": False,
                "feedback": "Question not found. Try starting a new quiz.",
                "weak_concepts": self.engine.weak_concepts,
                "audio_url": None,
            }

        q = self._current_question
        result = await self.engine.evaluate_answer(
            question_text=q["text"],
            correct_answer=q["answer"],
            user_answer=user_answer,
            concept=q["concept"],
        )

        # Skip TTS — feedback is shown as text in the overlay
        return {
            "correct": result["correct"],
            "feedback": result["feedback"],
            "concept": result["concept"],
            "weak_concepts": result["weak_concepts"],
            "audio_url": None,
        }
