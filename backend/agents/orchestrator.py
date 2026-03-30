"""Central coordinator — routes to speaker agents, supports Live API streaming."""

import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from sqlmodel import Session, select

from google import genai
from google.genai import types

from config import settings
from models.db import Paper, PodcastTurn, QAEntry, Session as SessionModel
from agents.host import HostAgent
from agents.expert import ExpertAgent
from agents.skeptic import SkepticAgent
from agents.retrieval_agent import RetrievalAgent
from services.live_api import LiveSession, build_live_system_instruction, pcm_chunks_to_wav
from services.tts import generate_turn_audio
from prompts.host import HOST_SYSTEM_PROMPT, HOST_BEGINNER_ADDENDUM, HOST_TECHNICAL_ADDENDUM
from prompts.expert import EXPERT_SYSTEM_PROMPT, EXPERT_BEGINNER_ADDENDUM, EXPERT_TECHNICAL_ADDENDUM
from prompts.skeptic import SKEPTIC_SYSTEM_PROMPT, SKEPTIC_BEGINNER_ADDENDUM, SKEPTIC_TECHNICAL_ADDENDUM

logger = logging.getLogger(__name__)

SKEPTIC_KEYWORDS = [
    "limitation", "limited", "trust", "valid", "wrong", "weak", "flaw",
    "bias", "biased", "problem", "issue", "concern", "doubt", "critique",
    "criticism", "reliable", "trustworthy", "accurate", "fair",
]

SPEAKER_PROMPTS = {
    "host": HOST_SYSTEM_PROMPT,
    "expert": EXPERT_SYSTEM_PROMPT,
    "skeptic": SKEPTIC_SYSTEM_PROMPT,
}


@dataclass
class InteractionResponse:
    """Non-streaming response (fallback)."""
    speaker: str
    text: str
    audio_url: Optional[str] = None
    resume_text: Optional[str] = None
    resume_audio_url: Optional[str] = None


class Orchestrator:
    """Routes user interactions to the correct speaker agent.

    Supports two modes:
    - Streaming (Live API): for real-time audio responses via WebSocket
    - Non-streaming (TTS fallback): generates complete audio files
    """

    def __init__(self, session_id: str, db: Session):
        self.session_id = session_id
        self.db = db

        self.session = db.get(SessionModel, session_id)
        if not self.session:
            raise ValueError(f"Session {session_id} not found")

        self.paper = db.get(Paper, self.session.paper_id)
        if not self.paper or not self.paper.knowledge_pack_json:
            raise ValueError("Paper or knowledge pack not found")

        self.knowledge_pack = json.loads(self.paper.knowledge_pack_json)
        self.difficulty = self.session.difficulty or "beginner"

        # Text-based agents (for non-streaming fallback)
        self.host = HostAgent(self.knowledge_pack, difficulty=self.difficulty)
        self.expert = ExpertAgent(self.knowledge_pack, difficulty=self.difficulty)
        self.skeptic = SkepticAgent(self.knowledge_pack, difficulty=self.difficulty)
        self.retrieval = RetrievalAgent(self.paper.id)

        # Single shared Live session (lazy-initialized)
        self._live_session: Optional[LiveSession] = None

    async def _get_live_session(self) -> LiveSession:
        """Get or create the shared Live API session with full paper context."""
        if self._live_session is None:
            paper_context = self._build_paper_context()
            kp = self.knowledge_pack
            title = kp.get("title", "Unknown Paper")

            difficulty_note = (
                "Use simple language, avoid jargon, include analogies."
                if self.difficulty == "beginner"
                else "Use precise technical language appropriate for a graduate audience."
            )

            system_prompt = f"""You are the Expert speaker on a podcast discussing the paper: "{title}".

Your personality: Clear, authoritative, educational. You explain methods, results, and significance. You connect ideas back to the source paper.

When a listener asks a question, comments, or requests a deeper/simpler explanation:
1. Always respond as the Expert. Start with [Expert].
2. Respond in 2-4 natural sentences.
3. Ground your answer in the paper context below.
4. Never use LaTeX, math symbols ($, \\, ^, _), or code. Write all math as spoken English.

{difficulty_note}

--- PAPER CONTEXT ---
{paper_context}
"""
            live = LiveSession(
                system_instruction=system_prompt,
                speaker="expert",  # Uses Puck voice — consistent with Expert TTS
                paper_context="",  # Already in system instruction
            )
            await live.connect()
            self._live_session = live
        return self._live_session

    def _build_paper_context(self) -> str:
        """Build condensed paper context for Live API grounding."""
        kp = self.knowledge_pack
        parts = [
            f"Title: {kp.get('title', '')}",
            f"Summary: {kp.get('one_sentence_summary', '')}",
        ]
        claims = kp.get("core_claims", [])
        if claims:
            parts.append("Core claims:\n" + "\n".join(f"- {c}" for c in claims[:5]))
        methods = kp.get("methods", [])
        if methods:
            parts.append("Methods:\n" + "\n".join(f"- {m.get('name', '')}: {m.get('description', '')}" for m in methods[:3]))
        limitations = kp.get("limitations", [])
        if limitations:
            parts.append("Limitations:\n" + "\n".join(f"- {l}" for l in limitations[:5]))
        glossary = kp.get("glossary", [])
        if glossary:
            parts.append("Key terms:\n" + "\n".join(f"- {g.get('term', '')}: {g.get('definition', '')}" for g in glossary[:8]))
        return "\n\n".join(parts)

    # --- Streaming mode (Live API) ---

    async def handle_interruption_streaming(
        self,
        question: str,
        current_turn_index: int,
    ) -> AsyncIterator[dict]:
        """Handle an interruption with streaming audio via Live API.

        Yields dicts:
          {"type": "audio", "data": bytes, "mime_type": str}
          {"type": "transcript", "text": str, "full_text": str}
          {"type": "turn_complete", "speaker": str, "full_transcript": str}
          {"type": "resume_audio", "data": bytes, "mime_type": str}
          {"type": "resume_transcript", "text": str}
          {"type": "resume_complete"}
        """
        # Retrieve context chunks and build grounding text
        context_chunks = await self.retrieval.retrieve(question, self.db)
        context_text = "\n".join(c["text"] for c in context_chunks[:3])

        logger.info(f"Live API: sending question: {question[:60]}...")

        # Get shared Live session (has paper context + speaker routing in system prompt)
        live = await self._get_live_session()

        # Build grounded question
        grounded_question = question
        if context_text:
            grounded_question = f"{question}\n\n[Relevant paper context]:\n{context_text}"

        # Stream the answer — Gemini decides which speaker answers
        full_transcript = ""
        speaker = "expert"  # default, will be parsed from transcript
        async for chunk in live.send_text_and_stream_audio(grounded_question):
            if chunk["type"] == "audio":
                yield {"type": "audio", "data": chunk["data"], "mime_type": chunk.get("mime_type", "audio/pcm")}
            elif chunk["type"] == "transcript":
                text = chunk.get("full_text", "")
                full_transcript = text
                # Parse speaker from transcript prefix like "[Expert]" or "[Skeptic]"
                if "[Skeptic]" in text or "[skeptic]" in text:
                    speaker = "skeptic"
                elif "[Expert]" in text or "[expert]" in text:
                    speaker = "expert"
                yield {"type": "transcript", "text": chunk["text"], "full_text": text}
            elif chunk["type"] == "turn_complete":
                full_transcript = chunk.get("full_transcript", full_transcript)
                yield {"type": "turn_complete", "speaker": speaker, "full_transcript": full_transcript}

        # Save Q&A entry
        qa = QAEntry(
            session_id=self.session_id,
            question=question,
            answer=full_transcript,
            speaker=speaker,
            turn_index_at=current_turn_index,
        )
        self.db.add(qa)
        self.db.commit()

        # Stream host resume line — include context of interrupted + next turn
        current_turn = self._get_turn(current_turn_index)
        next_turn = self._get_turn(current_turn_index + 1)
        resume_turn_index = current_turn_index + 1

        interrupted_text = current_turn.text if current_turn else ""
        next_speaker = next_turn.speaker if next_turn else "the expert"
        next_text = next_turn.text[:150] if next_turn else ""

        resume_prompt = f"""You are now speaking ONLY as the Host (NOT Expert, NOT Skeptic). Do NOT start with [Expert] or [Skeptic]. You are the Host.

Create a smooth, brief transition back to the podcast discussion.
We just had a deeper discussion about: "{interrupted_text[:200]}"
The next speaker ({next_speaker}) will say: "{next_text}"

Bridge naturally from what was just discussed into that next point. Keep it to 1-2 sentences. Speak as the Host — friendly, guiding, conversational. Never use LaTeX or math symbols."""

        # Tell frontend which turn to resume from
        yield {"type": "resume_from_turn", "turn_index": resume_turn_index}

        async for chunk in live.send_text_and_stream_audio(resume_prompt):
            if chunk["type"] == "audio":
                yield {"type": "resume_audio", "data": chunk["data"], "mime_type": chunk.get("mime_type", "audio/pcm")}
            elif chunk["type"] == "transcript":
                yield {"type": "resume_transcript", "text": chunk["text"]}
            elif chunk["type"] == "turn_complete":
                yield {"type": "resume_complete"}

    async def handle_voice_interruption_streaming(
        self,
        audio_data: bytes,
        current_turn_index: int,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
    ) -> AsyncIterator[dict]:
        """Handle a voice interruption via Live API.

        Sends audio directly to the shared Live session. Gemini hears
        the user's voice, decides which speaker should answer, and
        streams back an audio response.

        Also transcribes the audio separately so the frontend can show
        what the user said.
        """
        # Step 1: Transcribe the user's audio so we can show it in the UI
        from services.live_api import pcm_chunks_to_wav
        wav_data = pcm_chunks_to_wav([audio_data], sample_rate=sample_rate)

        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            transcription_response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=wav_data, mime_type="audio/wav"),
                            types.Part.from_text(text="Transcribe this audio exactly. Return ONLY the spoken words, nothing else."),
                        ],
                    ),
                ],
            )
            user_question = transcription_response.text.strip()
            logger.info(f"Voice transcribed: {user_question[:80]}")
        except Exception as e:
            logger.warning(f"Voice transcription failed: {e}")
            user_question = ""

        if user_question:
            yield {"type": "user_transcript", "text": user_question}

        # Step 2: Send transcribed text through the Live API text path
        # (more reliable than send_realtime_input with raw audio)
        question = user_question or "Can you tell me more about this paper?"
        async for chunk in self.handle_interruption_streaming(question, current_turn_index):
            yield chunk

    # --- Non-streaming fallback (TTS) ---

    async def handle_interruption(
        self,
        question: str,
        current_turn_index: int,
    ) -> InteractionResponse:
        """Handle interruption with pre-rendered TTS (fallback if Live API fails)."""
        context_chunks = await self.retrieval.retrieve(question, self.db)
        conversation_history = self._get_conversation_history()
        speaker_agent = self._route_agent(question)

        answer_text = await speaker_agent.respond(question, context_chunks, conversation_history)

        audio_url = await generate_turn_audio(
            text=answer_text, speaker=speaker_agent.role,
            session_id=self.session_id, turn_index=9000 + current_turn_index,
        )

        qa = QAEntry(
            session_id=self.session_id, question=question, answer=answer_text,
            speaker=speaker_agent.role, turn_index_at=current_turn_index,
        )
        self.db.add(qa)
        self.db.commit()

        current_turn = self._get_turn(current_turn_index)
        last_topic = current_turn.section if current_turn else "the paper"
        last_speaker = current_turn.speaker if current_turn else "expert"

        resume_text = await self.host.generate_resume(last_topic, last_speaker)
        resume_audio_url = await generate_turn_audio(
            text=resume_text, speaker="host",
            session_id=self.session_id, turn_index=9500 + current_turn_index,
        )

        return InteractionResponse(
            speaker=speaker_agent.role, text=answer_text, audio_url=audio_url,
            resume_text=resume_text, resume_audio_url=resume_audio_url,
        )

    async def handle_simplify(self, current_turn_index: int) -> InteractionResponse:
        current_turn = self._get_turn(current_turn_index)
        topic = current_turn.text if current_turn else "the current topic"
        return await self.handle_interruption(
            f"Can you explain this more simply? The topic was: {topic[:200]}", current_turn_index,
        )

    async def handle_go_deeper(self, current_turn_index: int) -> InteractionResponse:
        current_turn = self._get_turn(current_turn_index)
        topic = current_turn.text if current_turn else "the current topic"
        return await self.handle_interruption(
            f"Can you go deeper on this? The topic was: {topic[:200]}", current_turn_index,
        )

    # --- Warm-up & Cleanup ---

    async def warm_up_live_session(self):
        """Pre-connect the Live API session for faster first interaction."""
        try:
            await self._get_live_session()
            logger.info("Live API session pre-connected")
        except Exception as e:
            logger.warning(f"Live API warm-up failed (will retry on first use): {e}")

    async def close_live_sessions(self):
        """Close the Live API session."""
        if self._live_session:
            await self._live_session.close()
            self._live_session = None

    # --- Routing ---

    def _route_speaker(self, question: str) -> str:
        """Route to speaker name string."""
        q = question.lower()
        for kw in SKEPTIC_KEYWORDS:
            if kw in q:
                return "skeptic"
        return "expert"

    def _route_agent(self, question: str) -> HostAgent | ExpertAgent | SkepticAgent:
        """Route to speaker agent object (for non-streaming)."""
        speaker = self._route_speaker(question)
        return {"host": self.host, "expert": self.expert, "skeptic": self.skeptic}[speaker]

    def _get_conversation_history(self) -> list[dict]:
        turns = self.db.exec(
            select(PodcastTurn).where(PodcastTurn.session_id == self.session_id)
            .order_by(PodcastTurn.turn_index)
        ).all()
        history = [{"speaker": t.speaker, "text": t.text, "is_user": False} for t in turns[-6:]]

        qas = self.db.exec(
            select(QAEntry).where(QAEntry.session_id == self.session_id)
            .order_by(QAEntry.created_at)
        ).all()
        for qa in qas[-3:]:
            history.append({"speaker": "user", "text": qa.question, "is_user": True})
            history.append({"speaker": qa.speaker, "text": qa.answer, "is_user": False})
        return history

    def _get_turn(self, index: int) -> Optional[PodcastTurn]:
        results = self.db.exec(
            select(PodcastTurn).where(PodcastTurn.session_id == self.session_id)
            .where(PodcastTurn.turn_index == index)
        ).all()
        return results[0] if results else None
