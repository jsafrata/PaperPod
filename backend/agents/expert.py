"""Expert agent — explanations, technical clarification, figure walkthroughs."""

import logging
from google import genai
from google.genai import types

from config import settings
from prompts.expert import EXPERT_SYSTEM_PROMPT, EXPERT_BEGINNER_ADDENDUM, EXPERT_TECHNICAL_ADDENDUM

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3-flash-preview"


class ExpertAgent:
    role = "expert"

    def __init__(self, knowledge_pack: dict, difficulty: str = "beginner"):
        self.kp = knowledge_pack
        self.difficulty = difficulty
        self.history: list[dict] = []

    async def respond(self, question: str, context_chunks: list[dict], conversation_history: list[dict]) -> str:
        """Generate an expert response grounded in paper context."""
        client = genai.Client(api_key=settings.gemini_api_key)

        context_text = "\n\n".join(c["text"] for c in context_chunks[:5])
        glossary = self.kp.get("glossary", [])
        glossary_text = "\n".join(f"- {g['term']}: {g['definition']}" for g in glossary[:10])

        recent_history = conversation_history[-6:]
        messages = []
        for entry in recent_history:
            role = "user" if entry.get("is_user") else "model"
            messages.append(types.Content(role=role, parts=[types.Part.from_text(text=entry["text"])]))

        messages.append(types.Content(
            role="user",
            parts=[types.Part.from_text(
                text=f"[User asks]: {question}\n\n[Relevant paper context]:\n{context_text}\n\n[Key terms]:\n{glossary_text}"
            )],
        ))

        difficulty_addendum = EXPERT_BEGINNER_ADDENDUM if self.difficulty == "beginner" else EXPERT_TECHNICAL_ADDENDUM
        system = EXPERT_SYSTEM_PROMPT + difficulty_addendum + f"\n\nPaper: {self.kp.get('title', 'Unknown')}\nSummary: {self.kp.get('one_sentence_summary', '')}"

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.5,
                max_output_tokens=400,
            ),
        )

        answer = response.text.strip()
        self.history.append({"q": question, "a": answer})
        return answer
