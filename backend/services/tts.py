"""Gemini TTS — per-turn audio generation with parallel execution."""

import asyncio
import base64
import io
import logging
import wave
import struct
from typing import Optional

from google import genai
from google.genai import types
from sqlmodel import Session, select

from config import settings
from models.db import PodcastTurn
from storage.supabase import upload_file

logger = logging.getLogger(__name__)

# Gemini model for TTS
TTS_MODEL = "gemini-2.5-flash-preview-tts"

# Speaker voice mapping — distinct Gemini voices for each role
SPEAKER_VOICES = {
    "host": "Kore",       # warm, guiding
    "expert": "Puck",     # clear, confident
    "skeptic": "Charon",  # measured, probing
}

# Max concurrent TTS calls (rate limiting)
# Note: semaphore created per-call in generate_all_turn_audio to avoid cross-event-loop issues
TTS_CONCURRENCY = 5


def _get_genai_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def generate_turn_audio(
    text: str,
    speaker: str,
    session_id: str,
    turn_index: int,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Optional[str]:
    """Generate TTS audio for a single turn. Returns Supabase public URL or None."""
    voice_name = SPEAKER_VOICES.get(speaker, "Kore")

    async with (semaphore or asyncio.Semaphore(1)):
        try:
            client = _get_genai_client()

            # Run synchronous Gemini call in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: client.models.generate_content(
                model=TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                ),
            ))

            # Extract audio data from response (with retry on empty response)
            if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                # Retry once
                logger.warning(f"TTS empty response for turn {turn_index}, retrying...")
                response = await loop.run_in_executor(None, lambda: client.models.generate_content(
                    model=TTS_MODEL,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name,
                                )
                            )
                        ),
                    ),
                ))
                if not response.candidates or not response.candidates[0].content or not response.candidates[0].content.parts:
                    logger.error(f"TTS retry also empty for turn {turn_index}")
                    return None

            audio_data = response.candidates[0].content.parts[0].inline_data.data
            mime_type = response.candidates[0].content.parts[0].inline_data.mime_type

            # The response is raw PCM audio — convert to WAV
            if "pcm" in (mime_type or "").lower() or not mime_type:
                wav_bytes = _pcm_to_wav(audio_data, sample_rate=24000, channels=1, sample_width=2)
            else:
                wav_bytes = audio_data

            # Upload to Supabase Storage
            storage_path = f"{session_id}/{turn_index}.wav"
            try:
                audio_url = upload_file("audio", storage_path, wav_bytes, "audio/wav")
                return audio_url
            except Exception as e:
                logger.warning(f"Supabase audio upload failed for turn {turn_index}: {e}")
                return None

        except Exception as e:
            logger.error(f"TTS generation failed for turn {turn_index} ({speaker}): {e}")
            return None


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Convert raw PCM audio data to WAV format."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


async def generate_all_turn_audio(
    session_id: str,
    db: Session,
) -> int:
    """Generate TTS audio for all turns in a session. Returns count of successful generations.

    Runs TTS calls in parallel with a semaphore for rate limiting.
    """
    turns = db.exec(
        select(PodcastTurn)
        .where(PodcastTurn.session_id == session_id)
        .order_by(PodcastTurn.turn_index)
    ).all()

    if not turns:
        logger.warning(f"No turns found for session {session_id}")
        return 0

    # Skip turns that already have audio (e.g. recovery after restart)
    turns_needing_audio = [t for t in turns if not t.audio_url]
    if not turns_needing_audio:
        logger.info(f"All {len(turns)} turns already have audio, nothing to generate")
        return len(turns)

    # Create semaphore in the current event loop (avoids cross-loop issues)
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)
    logger.info(f"Generating TTS for {len(turns_needing_audio)}/{len(turns)} turns (parallel, max {TTS_CONCURRENCY} concurrent)...")

    async def _process_turn(turn: PodcastTurn) -> bool:
        audio_url = await generate_turn_audio(
            text=turn.text,
            speaker=turn.speaker,
            session_id=session_id,
            turn_index=turn.turn_index,
            semaphore=semaphore,
        )
        if audio_url:
            turn.audio_url = audio_url
            turn.audio_storage_path = f"{session_id}/{turn.turn_index}.wav"
            return True
        return False

    # Run TTS in parallel for turns that need it
    results = await asyncio.gather(
        *[_process_turn(turn) for turn in turns_needing_audio],
        return_exceptions=True,
    )

    newly_generated = sum(1 for r in results if r is True)
    already_had = len(turns) - len(turns_needing_audio)
    success_count = newly_generated + already_had
    db.commit()

    logger.info(f"TTS complete: {success_count}/{len(turns)} turns generated successfully")
    return success_count


async def generate_remaining_turn_audio(
    session_id: str,
    db: Session,
    from_index: int,
) -> int:
    """Generate TTS for turns starting from a specific index. For background completion."""
    turns = db.exec(
        select(PodcastTurn)
        .where(PodcastTurn.session_id == session_id)
        .where(PodcastTurn.turn_index >= from_index)
        .order_by(PodcastTurn.turn_index)
    ).all()

    turns_needing_audio = [t for t in turns if not t.audio_url]
    if not turns_needing_audio:
        return 0

    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)
    logger.info(f"Background TTS: {len(turns_needing_audio)} remaining turns for session {session_id}")

    async def _process_turn(turn: PodcastTurn) -> bool:
        audio_url = await generate_turn_audio(
            text=turn.text,
            speaker=turn.speaker,
            session_id=session_id,
            turn_index=turn.turn_index,
            semaphore=semaphore,
        )
        if audio_url:
            turn.audio_url = audio_url
            turn.audio_storage_path = f"{session_id}/{turn.turn_index}.wav"
            return True
        return False

    results = await asyncio.gather(
        *[_process_turn(turn) for turn in turns_needing_audio],
        return_exceptions=True,
    )

    count = sum(1 for r in results if r is True)
    db.commit()
    logger.info(f"Background TTS complete: {count} turns")
    return count
