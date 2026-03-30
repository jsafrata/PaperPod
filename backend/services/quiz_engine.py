"""Dynamic quiz question generation + answer evaluation."""

import json
import logging
import uuid
from typing import Optional

from google import genai
from google.genai import types
from sqlmodel import Session, select

from config import settings
from models.db import Paper, PodcastTurn, QAEntry, QuizAttempt, Session as SessionModel
from prompts.quiz import QUIZ_GENERATION_PROMPT, QUIZ_EVALUATION_PROMPT, QUIZ_BEGINNER_INSTRUCTION, QUIZ_TECHNICAL_INSTRUCTION

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"


class QuizEngine:
    """Generates quiz questions dynamically and evaluates answers."""

    def __init__(self, session_id: str, db: Session):
        self.session_id = session_id
        self.db = db

        session = db.get(SessionModel, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        self.difficulty = session.difficulty or "beginner"

        paper = db.get(Paper, session.paper_id)
        if not paper or not paper.knowledge_pack_json:
            raise ValueError("Paper or knowledge pack not found")

        self.knowledge_pack = json.loads(paper.knowledge_pack_json)
        self.paper_title = self.knowledge_pack.get("title", "Unknown")

        # Load previous quiz questions for this session (avoid repeats)
        attempts = db.exec(
            select(QuizAttempt)
            .where(QuizAttempt.session_id == session_id)
            .order_by(QuizAttempt.created_at)
        ).all()
        self.previous_questions = [a.question_text for a in attempts]

        # Track weak concepts
        self.weak_concepts = list(set(
            a.concept for a in attempts if not a.correct
        ))

    async def generate_question(
        self,
        section: Optional[str] = None,
        conversation_history: str = "",
    ) -> Optional[dict]:
        """Generate a single quiz question dynamically using Gemini."""
        client = genai.Client(api_key=settings.gemini_api_key)

        # Build paper summary from knowledge pack
        kp = self.knowledge_pack
        paper_summary = json.dumps({
            "title": kp.get("title", ""),
            "summary": kp.get("one_sentence_summary", ""),
            "core_claims": kp.get("core_claims", []),
            "methods": [m.get("name", "") + ": " + m.get("description", "") for m in kp.get("methods", [])],
            "results": [r.get("finding", "") for r in kp.get("results", [])],
            "limitations": kp.get("limitations", []),
            "glossary": [g.get("term", "") + ": " + g.get("definition", "") for g in kp.get("glossary", [])],
        }, indent=2)

        prompt = QUIZ_GENERATION_PROMPT.format(
            paper_summary=paper_summary,
            current_section=section or "general",
            conversation_history=conversation_history or "No conversation yet.",
            previous_questions="\n".join(f"- {q}" for q in self.previous_questions) or "None yet.",
            weak_concepts=", ".join(self.weak_concepts) if self.weak_concepts else "None identified yet.",
            difficulty_instruction=QUIZ_BEGINNER_INSTRUCTION if self.difficulty == "beginner" else QUIZ_TECHNICAL_INSTRUCTION,
        )

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                )],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                ),
            ))

            result = json.loads(response.text.strip())
            question_id = str(uuid.uuid4())

            return {
                "question_id": question_id,
                "text": result.get("question", ""),
                "answer": result.get("answer", ""),
                "concept": result.get("concept", ""),
                "difficulty": result.get("difficulty", "medium"),
                "section": section or "general",
            }
        except Exception as e:
            logger.error(f"Quiz question generation failed: {e}")
            return None

    async def evaluate_answer(
        self,
        question_text: str,
        correct_answer: str,
        user_answer: str,
        concept: str,
    ) -> dict:
        """Evaluate a user's answer using Gemini."""
        client = genai.Client(api_key=settings.gemini_api_key)

        prompt = QUIZ_EVALUATION_PROMPT.format(
            paper_title=self.paper_title,
            question=question_text,
            correct_answer=correct_answer,
            user_answer=user_answer,
        )

        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )],
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        ))

        result = json.loads(response.text.strip())
        is_correct = result.get("correct", False)
        feedback = result.get("feedback", "")
        evaluated_concept = result.get("concept", concept)

        # Save attempt
        attempt = QuizAttempt(
            session_id=self.session_id,
            question_text=question_text,
            user_answer=user_answer,
            correct=is_correct,
            concept=evaluated_concept,
            feedback=feedback,
        )
        self.db.add(attempt)
        self.db.commit()

        # Update tracking
        self.previous_questions.append(question_text)
        if not is_correct and evaluated_concept not in self.weak_concepts:
            self.weak_concepts.append(evaluated_concept)

        # Update session weak concepts
        session = self.db.get(SessionModel, self.session_id)
        if session:
            session.weak_concepts_json = json.dumps(self.weak_concepts)
            self.db.commit()

        return {
            "correct": is_correct,
            "feedback": feedback,
            "concept": evaluated_concept,
            "weak_concepts": self.weak_concepts,
        }
