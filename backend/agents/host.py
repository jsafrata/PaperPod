"""Host agent — framing, transitions, recaps, resume after interruption."""

import logging
from google import genai
from google.genai import types

from config import settings
from prompts.host import HOST_SYSTEM_PROMPT, HOST_BEGINNER_ADDENDUM, HOST_TECHNICAL_ADDENDUM

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3-flash-preview"


class HostAgent:
    role = "host"

    def __init__(self, knowledge_pack: dict, difficulty: str = "beginner"):
        self.kp = knowledge_pack
        self.difficulty = difficulty
        self.history: list[dict] = []

    def _system_prompt(self) -> str:
        addendum = HOST_BEGINNER_ADDENDUM if self.difficulty == "beginner" else HOST_TECHNICAL_ADDENDUM
        return HOST_SYSTEM_PROMPT + addendum + f"\n\nPaper: {self.kp.get('title', 'Unknown')}"

    async def respond(self, question: str, context_chunks: list[dict], conversation_history: list[dict]) -> str:
        """Generate a host response to a user question or for a transition."""
        client = genai.Client(api_key=settings.gemini_api_key)

        context_text = "\n\n".join(c["text"] for c in context_chunks[:3])
        recent_history = conversation_history[-6:]

        messages = []
        for entry in recent_history:
            role = "user" if entry.get("is_user") else "model"
            messages.append(types.Content(role=role, parts=[types.Part.from_text(text=entry["text"])]))

        messages.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"[User asks]: {question}\n\n[Relevant paper context]:\n{context_text}")],
        ))

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=self._system_prompt(),
                temperature=0.7,
                max_output_tokens=300,
            ),
        )

        answer = response.text.strip()
        self.history.append({"q": question, "a": answer})
        return answer

    async def generate_resume(self, last_topic: str, last_speaker: str) -> str:
        """Generate a brief transition line to resume the podcast after Q&A."""
        client = genai.Client(api_key=settings.gemini_api_key)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(
                    text=f"The podcast was discussing: {last_topic}. The last speaker was the {last_speaker}. Generate a brief 1-2 sentence transition to resume the discussion naturally."
                )],
            )],
            config=types.GenerateContentConfig(
                system_instruction=self._system_prompt(),
                temperature=0.7,
                max_output_tokens=150,
            ),
        )
        return response.text.strip()
