"""Skeptic agent — limitations, criticism, trustworthiness."""

import logging
from google import genai
from google.genai import types

from config import settings
from prompts.skeptic import SKEPTIC_SYSTEM_PROMPT, SKEPTIC_BEGINNER_ADDENDUM, SKEPTIC_TECHNICAL_ADDENDUM

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3-flash-preview"


class SkepticAgent:
    role = "skeptic"

    def __init__(self, knowledge_pack: dict, difficulty: str = "beginner"):
        self.kp = knowledge_pack
        self.difficulty = difficulty
        self.history: list[dict] = []

    async def respond(self, question: str, context_chunks: list[dict], conversation_history: list[dict]) -> str:
        """Generate a skeptic response highlighting limitations and uncertainty."""
        client = genai.Client(api_key=settings.gemini_api_key)

        context_text = "\n\n".join(c["text"] for c in context_chunks[:5])
        limitations = self.kp.get("limitations", [])
        limitations_text = "\n".join(f"- {l}" for l in limitations)

        recent_history = conversation_history[-6:]
        messages = []
        for entry in recent_history:
            role = "user" if entry.get("is_user") else "model"
            messages.append(types.Content(role=role, parts=[types.Part.from_text(text=entry["text"])]))

        messages.append(types.Content(
            role="user",
            parts=[types.Part.from_text(
                text=f"[User asks]: {question}\n\n[Relevant paper context]:\n{context_text}\n\n[Known limitations]:\n{limitations_text}"
            )],
        ))

        difficulty_addendum = SKEPTIC_BEGINNER_ADDENDUM if self.difficulty == "beginner" else SKEPTIC_TECHNICAL_ADDENDUM
        system = SKEPTIC_SYSTEM_PROMPT + difficulty_addendum + f"\n\nPaper: {self.kp.get('title', 'Unknown')}"

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.6,
                max_output_tokens=400,
            ),
        )

        answer = response.text.strip()
        self.history.append({"q": question, "a": answer})
        return answer
