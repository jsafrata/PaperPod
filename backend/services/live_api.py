"""Gemini Live API service for real-time voice Q&A.

Used for interactive interruptions — streams audio responses back
with much lower latency than the TTS → upload → URL flow.
"""

import asyncio
import base64
import io
import logging
import wave
from typing import AsyncIterator, Optional

from google import genai
from google.genai import types

from config import settings

logger = logging.getLogger(__name__)

LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"

SPEAKER_VOICES = {
    "host": "Kore",
    "expert": "Puck",
    "skeptic": "Charon",
}


class LiveSession:
    """Manages a Gemini Live API session for a podcast interaction.

    Supports:
    - Text input → streaming audio output (for text-based interrupts)
    - Audio input → streaming audio output (for voice interrupts)
    - Conversation context via system instruction
    """

    def __init__(
        self,
        system_instruction: str,
        speaker: str = "expert",
        paper_context: str = "",
    ):
        self.system_instruction = system_instruction
        self.speaker = speaker
        self.paper_context = paper_context
        self.voice_name = SPEAKER_VOICES.get(speaker, "Puck")
        self._session = None
        self._ctx = None
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def connect(self):
        """Open a Live API session."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name,
                    )
                )
            ),
            system_instruction=self.system_instruction,
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        # Use the async context manager to get the session
        self._ctx = self._client.aio.live.connect(
            model=LIVE_MODEL,
            config=config,
        )
        self._session = await self._ctx.__aenter__()

        # Send paper context as initial grounding
        if self.paper_context:
            await self._session.send_client_content(
                turns=[types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text=f"[Paper context for grounding your answers]:\n{self.paper_context}"
                    )],
                )],
                turn_complete=False,
            )

        logger.info(f"Live session connected (speaker={self.speaker}, voice={self.voice_name})")

    async def send_text_and_stream_audio(
        self,
        text: str,
    ) -> AsyncIterator[dict]:
        """Send a text message and stream back audio chunks + transcript.

        Yields dicts:
          {"type": "audio", "data": bytes}  — raw PCM audio chunk
          {"type": "transcript", "text": str}  — transcription of the response
          {"type": "turn_complete"}  — signals the response is done
        """
        if not self._session:
            raise RuntimeError("Live session not connected")

        await self._session.send_client_content(
            turns=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            )],
            turn_complete=True,
        )

        full_transcript = ""

        async for msg in self._session.receive():
            server_content = msg.server_content
            if not server_content:
                continue

            # Audio data from model turn
            if server_content.model_turn and server_content.model_turn.parts:
                for part in server_content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        yield {
                            "type": "audio",
                            "data": part.inline_data.data,
                            "mime_type": part.inline_data.mime_type or "audio/pcm",
                        }

            # Output transcription
            if server_content.output_transcription and server_content.output_transcription.text:
                full_transcript += server_content.output_transcription.text
                yield {
                    "type": "transcript",
                    "text": server_content.output_transcription.text,
                    "full_text": full_transcript,
                }

            # Turn complete
            if server_content.turn_complete:
                yield {"type": "turn_complete", "full_transcript": full_transcript}
                break

    async def send_audio_and_stream_response(
        self,
        audio_data: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
    ) -> AsyncIterator[dict]:
        """Send audio input and stream back audio response.

        Yields same dict types as send_text_and_stream_audio.
        """
        if not self._session:
            raise RuntimeError("Live session not connected")

        # Send audio as realtime input
        await self._session.send_realtime_input(
            audio=types.Blob(data=audio_data, mime_type=f"{mime_type};rate={sample_rate}"),
        )

        # Signal end of audio
        await self._session.send_realtime_input(audio_stream_end=True)

        full_transcript = ""

        async for msg in self._session.receive():
            server_content = msg.server_content
            if not server_content:
                continue

            if server_content.model_turn and server_content.model_turn.parts:
                for part in server_content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        yield {
                            "type": "audio",
                            "data": part.inline_data.data,
                            "mime_type": part.inline_data.mime_type or "audio/pcm",
                        }

            if server_content.output_transcription and server_content.output_transcription.text:
                full_transcript += server_content.output_transcription.text
                yield {
                    "type": "transcript",
                    "text": server_content.output_transcription.text,
                    "full_text": full_transcript,
                }

            if server_content.turn_complete:
                yield {"type": "turn_complete", "full_transcript": full_transcript}
                break

    async def close(self):
        """Close the Live API session."""
        if self._ctx:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
            self._ctx = None
            logger.info("Live session closed")


def build_live_system_instruction(
    speaker: str,
    paper_title: str,
    speaker_prompt: str,
) -> str:
    """Build the system instruction for a Live API session."""
    return (
        f"{speaker_prompt}\n\n"
        f"You are currently discussing the paper: {paper_title}\n\n"
        f"Keep responses concise (2-4 sentences). "
        f"Ground your answers in the paper context provided."
    )


def pcm_chunks_to_wav(chunks: list[bytes], sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Convert collected PCM audio chunks to a single WAV file."""
    pcm_data = b"".join(chunks)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()
