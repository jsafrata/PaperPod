"""Background podcast regeneration manager for style changes.

When a user requests a style change (e.g. "make it simpler"), this manager
regenerates remaining turns in the background — one at a time — and sends
each updated turn to the frontend via WebSocket as soon as its TTS is ready.
"""

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import WebSocket
from sqlmodel import Session as DBSession, select

from models.db import PodcastTurn, Session as SessionModel
from services.script_generator import generate_restyled_script
from services.tts import generate_turn_audio

logger = logging.getLogger(__name__)


class RestyleManager:
    """Manages one active restyle task per session with cooperative cancellation."""

    def __init__(self):
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._generation_ids: dict[str, str] = {}

    async def start_restyle(
        self,
        session_id: str,
        directive: str,
        from_turn_index: int,
        websocket: WebSocket,
        db: DBSession,
    ) -> None:
        """Cancel any existing restyle and start a new background regeneration."""
        # Cancel previous restyle for this session
        await self.cancel_restyle(session_id)

        generation_id = str(uuid.uuid4())
        self._generation_ids[session_id] = generation_id

        # Persist directive on session
        session = db.get(SessionModel, session_id)
        if session:
            session.style_directive = directive
            db.commit()

        task = asyncio.create_task(
            self._run_restyle(
                session_id=session_id,
                directive=directive,
                from_turn_index=from_turn_index,
                generation_id=generation_id,
                websocket=websocket,
                db=db,
            )
        )
        self._active_tasks[session_id] = task

    async def cancel_restyle(self, session_id: str) -> None:
        """Cancel active restyle for a session."""
        old_task = self._active_tasks.pop(session_id, None)
        if old_task and not old_task.done():
            old_task.cancel()
            try:
                await old_task
            except (asyncio.CancelledError, Exception):
                pass

        # Clear generation_id so any lingering coroutine stops cooperatively
        self._generation_ids.pop(session_id, None)

    def _is_current(self, session_id: str, generation_id: str) -> bool:
        """Check if this generation is still the active one (cooperative cancellation)."""
        return self._generation_ids.get(session_id) == generation_id

    async def _process_and_send_turns(
        self,
        turns_data: list[dict],
        session_id: str,
        from_turn_index: int,
        start_offset: int,
        generation_id: str,
        websocket: WebSocket,
        db: DBSession,
    ) -> int:
        """Generate TTS for turns and send updates. Returns count of turns sent."""
        sent = 0
        for i, turn_data in enumerate(turns_data):
            if not self._is_current(session_id, generation_id):
                return sent

            actual_turn_index = from_turn_index + 1 + start_offset + i

            audio_url = await generate_turn_audio(
                text=turn_data["text"],
                speaker=turn_data["speaker"],
                session_id=session_id,
                turn_index=actual_turn_index,
            )

            if not self._is_current(session_id, generation_id):
                return sent

            # Update DB row
            db_turn = db.exec(
                select(PodcastTurn).where(
                    PodcastTurn.session_id == session_id,
                    PodcastTurn.turn_index == actual_turn_index,
                )
            ).first()

            if db_turn:
                db_turn.speaker = turn_data["speaker"]
                db_turn.text = turn_data["text"]
                db_turn.section = turn_data["section"]
                db_turn.visual_id = turn_data.get("visual_id")
                db_turn.audio_url = audio_url
                if audio_url:
                    db_turn.audio_storage_path = f"{session_id}/{actual_turn_index}.wav"
                db.commit()

            # Only send update if TTS succeeded — otherwise keep original turn
            if audio_url:
                try:
                    await websocket.send_json({
                        "type": "turn_update",
                        "index": actual_turn_index,
                        "speaker": turn_data["speaker"],
                        "text": turn_data["text"],
                        "audio_url": audio_url,
                        "visual_id": turn_data.get("visual_id"),
                        "section": turn_data["section"],
                    })
                except Exception:
                    logger.warning(f"Restyle [{generation_id[:8]}]: WS send failed, stopping")
                    return sent
            else:
                logger.warning(f"Restyle [{generation_id[:8]}]: TTS failed for turn {actual_turn_index}, keeping original")

            sent += 1
            logger.info(f"Restyle [{generation_id[:8]}]: turn {actual_turn_index} ready")

        return sent

    async def _run_restyle(
        self,
        session_id: str,
        directive: str,
        from_turn_index: int,
        generation_id: str,
        websocket: WebSocket,
        db: DBSession,
    ) -> None:
        """Background task: two-phase restyle for fast first turn.

        Phase 1: Generate first 3 turns → send first turn immediately (text-only)
                 → TTS first turn → send updated turn with audio
        Phase 2: Generate + TTS remaining turns in background
        """
        try:
            # Phase 1: Generate first 3 turns quickly
            logger.info(f"Restyle [{generation_id[:8]}]: phase 1 — generating first 3 turns...")
            first_batch = await generate_restyled_script(
                session_id=session_id,
                db=db,
                from_turn_index=from_turn_index,
                style_directive=directive,
                max_turns=3,
            )

            if not self._is_current(session_id, generation_id) or not first_batch:
                return

            # TTS all first batch turns + send updates with audio (only if TTS succeeds)
            sent = await self._process_and_send_turns(
                first_batch, session_id, from_turn_index, 0,
                generation_id, websocket, db,
            )

            if not self._is_current(session_id, generation_id) or sent == 0:
                return

            # Phase 2: Generate remaining turns in background
            logger.info(f"Restyle [{generation_id[:8]}]: phase 2 — generating remaining turns...")
            remaining = await generate_restyled_script(
                session_id=session_id,
                db=db,
                from_turn_index=from_turn_index + len(first_batch),
                style_directive=directive,
            )

            if not self._is_current(session_id, generation_id):
                return

            if remaining:
                await self._process_and_send_turns(
                    remaining, session_id, from_turn_index, len(first_batch),
                    generation_id, websocket, db,
                )

            # All done
            if self._is_current(session_id, generation_id):
                try:
                    await websocket.send_json({"type": "restyle_complete"})
                except Exception:
                    pass
                logger.info(f"Restyle [{generation_id[:8]}]: complete")

        except asyncio.CancelledError:
            logger.info(f"Restyle [{generation_id[:8]}]: task cancelled")
        except Exception as e:
            logger.error(f"Restyle [{generation_id[:8]}]: failed: {e}", exc_info=True)
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Restyle failed: {str(e)}",
                })
            except Exception:
                pass
        finally:
            # Clean up if we're still the active task
            if self._active_tasks.get(session_id) and self._active_tasks[session_id].done():
                self._active_tasks.pop(session_id, None)
            if self._generation_ids.get(session_id) == generation_id:
                self._generation_ids.pop(session_id, None)
