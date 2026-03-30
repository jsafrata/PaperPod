"""WebSocket endpoint for real-time interaction during podcast sessions.

Supports two modes:
- Streaming (Live API): audio chunks streamed in real-time
- Fallback (TTS): pre-rendered audio URLs sent as complete messages
"""

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session as DBSession

from deps import engine
from agents.orchestrator import Orchestrator
from agents.quiz_agent import QuizAgent
from services.intent_classifier import classify_intent
from services.restyle_manager import RestyleManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interact"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time interaction during a podcast session."""
    await websocket.accept()

    if engine is None:
        await websocket.send_json({"type": "error", "message": "Database not configured"})
        await websocket.close()
        return

    orchestrator = None
    restyle_manager = RestyleManager()

    try:
        with DBSession(engine) as db:
            try:
                orchestrator = Orchestrator(session_id, db)
                quiz_agent = QuizAgent(session_id, db)
                # Pre-connect Live API so Go Deeper/Ask is instant
                asyncio.create_task(orchestrator.warm_up_live_session())
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
                await websocket.close()
                return

            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                msg_type = msg.get("type")

                try:
                    if msg_type == "interrupt":
                        question = msg.get("question", "")
                        turn_index = msg.get("current_turn_index", 0)
                        use_live = msg.get("use_live", True)

                        # Classify: is this a style change or a question?
                        intent, text = classify_intent(question)

                        if intent == "restyle":
                            await websocket.send_json({
                                "type": "restyle_started",
                                "directive": text,
                                "from_turn_index": turn_index + 1,
                            })
                            await restyle_manager.start_restyle(
                                session_id, text, turn_index, websocket, db,
                            )
                        elif use_live:
                            await asyncio.wait_for(
                                _handle_streaming_interrupt(
                                    websocket, orchestrator, question, turn_index,
                                ),
                                timeout=30,
                            )
                        else:
                            await asyncio.wait_for(
                                _handle_fallback_interrupt(
                                    websocket, orchestrator, question, turn_index,
                                ),
                                timeout=30,
                            )

                    elif msg_type == "voice_interrupt":
                        # Voice input: base64-encoded audio
                        # For now, voice is unreliable (requires Live API).
                        # Send a friendly error so frontend can unstick.
                        audio_b64 = msg.get("audio", "")
                        turn_index = msg.get("current_turn_index", 0)
                        sample_rate = msg.get("sample_rate", 16000)

                        try:
                            audio_data = base64.b64decode(audio_b64)
                            await asyncio.wait_for(
                                _handle_voice_interrupt(
                                    websocket, orchestrator, audio_data, turn_index, sample_rate,
                                ),
                                timeout=60,
                            )
                        except asyncio.TimeoutError:
                            logger.warning("Voice interrupt timed out after 60s")
                            await websocket.send_json({
                                "type": "error",
                                "message": "Voice input timed out. Please try typing your question instead.",
                            })
                        except Exception as ve:
                            logger.error(f"Voice interrupt failed: {ve}")
                            await websocket.send_json({
                                "type": "error",
                                "message": "Voice input failed. Please try typing your question instead.",
                            })

                    elif msg_type in ("simplify", "go_deeper"):
                        turn_index = msg.get("current_turn_index", 0)
                        print(f"[GO_DEEPER] Received {msg_type} at turn {turn_index}", flush=True)

                        if msg_type == "simplify":
                            restyle_prompt = "Rephrase the following in simpler language with everyday analogies, as if explaining to a smart non-expert. Keep it 2-4 sentences:"
                        else:
                            restyle_prompt = "Rephrase the following in more technical and detailed language, going deeper into the methodology. Keep it 2-4 sentences:"

                        # Get the next turn's text to restyle
                        next_turn = orchestrator._get_turn(turn_index + 1)
                        next_text = next_turn.text if next_turn else "Continue the discussion."
                        print(f"[GO_DEEPER] Next turn text: {next_text[:80]}...", flush=True)

                        # Stream restyled first turn via Live API (instant)
                        print(f"[GO_DEEPER] Starting Live API stream...", flush=True)
                        await _handle_streaming_interrupt(
                            websocket, orchestrator,
                            f"{restyle_prompt}\n\n\"{next_text}\"",
                            turn_index + 1,  # resume_from_turn will be turn_index + 2
                        )
                        print(f"[GO_DEEPER] Stream complete", flush=True)

                    elif msg_type == "quiz_start":
                        section = msg.get("section")
                        quiz_turn_index = msg.get("current_turn_index", 0)
                        question = await quiz_agent.start_quiz(section, quiz_turn_index)
                        if question:
                            await websocket.send_json({
                                "type": "quiz_question",
                                "question_id": question["question_id"],
                                "text": question["text"],
                                "speaker": "host",
                                "audio_url": question.get("audio_url"),
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": "No quiz questions available.",
                            })

                    elif msg_type == "quiz_answer":
                        question_id = msg.get("question_id", "")
                        answer = msg.get("answer", "")
                        result = await quiz_agent.evaluate(question_id, answer)
                        await websocket.send_json({
                            "type": "quiz_feedback",
                            "correct": result["correct"],
                            "explanation": result["feedback"],
                            "speaker": "expert",
                            "audio_url": result.get("audio_url"),
                            "weak_concepts": result.get("weak_concepts", []),
                        })

                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}",
                        })

                except Exception as e:
                    logger.error(f"Error handling {msg_type}: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to process request: {str(e)}",
                    })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        await restyle_manager.cancel_restyle(session_id)
        if orchestrator:
            await orchestrator.close_live_sessions()


async def _handle_streaming_interrupt(
    websocket: WebSocket,
    orchestrator: Orchestrator,
    question: str,
    turn_index: int,
):
    """Stream audio response via Live API."""
    print(f"[STREAM] Starting streaming interrupt for turn {turn_index}", flush=True)
    try:
        chunk_count = 0
        async for chunk in orchestrator.handle_interruption_streaming(question, turn_index):
            chunk_count += 1
            if chunk_count == 1:
                print(f"[STREAM] First chunk type: {chunk['type']}", flush=True)
            if chunk["type"] == "audio":
                await websocket.send_json({
                    "type": "audio_chunk",
                    "data": base64.b64encode(chunk["data"]).decode(),
                    "mime_type": chunk.get("mime_type", "audio/pcm"),
                })
            elif chunk["type"] == "transcript":
                await websocket.send_json({
                    "type": "transcript_delta",
                    "text": chunk["text"],
                    "full_text": chunk.get("full_text", ""),
                })
            elif chunk["type"] == "turn_complete":
                await websocket.send_json({
                    "type": "answer_complete",
                    "speaker": chunk["speaker"],
                    "text": chunk.get("full_transcript", ""),
                })
            elif chunk["type"] == "resume_from_turn":
                await websocket.send_json({
                    "type": "resume_from_turn",
                    "turn_index": chunk["turn_index"],
                })
            elif chunk["type"] == "resume_audio":
                await websocket.send_json({
                    "type": "resume_audio_chunk",
                    "data": base64.b64encode(chunk["data"]).decode(),
                    "mime_type": chunk.get("mime_type", "audio/pcm"),
                })
            elif chunk["type"] == "resume_transcript":
                await websocket.send_json({
                    "type": "resume_transcript_delta",
                    "text": chunk["text"],
                })
            elif chunk["type"] == "resume_complete":
                await websocket.send_json({"type": "resume_complete"})
        print(f"[STREAM] Done. Total chunks: {chunk_count}", flush=True)
    except Exception as e:
        print(f"[STREAM] FAILED: {e}", flush=True)
        logger.warning(f"Live API streaming failed, falling back to TTS: {e}")
        response = await orchestrator.handle_interruption(question, turn_index)
        await _send_fallback_response(websocket, response, turn_index)


async def _handle_voice_interrupt(
    websocket: WebSocket,
    orchestrator: Orchestrator,
    audio_data: bytes,
    turn_index: int,
    sample_rate: int,
):
    """Handle voice input via Live API."""
    try:
        async for chunk in orchestrator.handle_voice_interruption_streaming(
            audio_data, turn_index, sample_rate=sample_rate,
        ):
            if chunk["type"] == "user_transcript":
                # Transcribed voice input — send to frontend to update transcript
                await websocket.send_json({
                    "type": "user_transcript",
                    "text": chunk["text"],
                })
            elif chunk["type"] == "audio":
                await websocket.send_json({
                    "type": "audio_chunk",
                    "data": base64.b64encode(chunk["data"]).decode(),
                    "mime_type": chunk.get("mime_type", "audio/pcm"),
                })
            elif chunk["type"] == "transcript":
                await websocket.send_json({
                    "type": "transcript_delta",
                    "text": chunk["text"],
                    "full_text": chunk.get("full_text", ""),
                })
            elif chunk["type"] == "turn_complete":
                await websocket.send_json({
                    "type": "answer_complete",
                    "speaker": chunk["speaker"],
                    "text": chunk.get("full_transcript", ""),
                })
            elif chunk["type"] in ("resume_audio", "resume_transcript", "resume_complete"):
                if chunk["type"] == "resume_audio":
                    await websocket.send_json({
                        "type": "resume_audio_chunk",
                        "data": base64.b64encode(chunk["data"]).decode(),
                        "mime_type": chunk.get("mime_type", "audio/pcm"),
                    })
                elif chunk["type"] == "resume_transcript":
                    await websocket.send_json({
                        "type": "resume_transcript_delta", "text": chunk["text"],
                    })
                else:
                    await websocket.send_json({"type": "resume_complete"})
    except Exception as e:
        logger.error(f"Voice interrupt failed: {e}", exc_info=True)
        await websocket.send_json({"type": "error", "message": str(e)})


async def _send_fallback_response(websocket: WebSocket, response, turn_index: int):
    """Send a non-streaming (TTS) response."""
    await websocket.send_json({
        "type": "answer",
        "speaker": response.speaker,
        "text": response.text,
        "audio_url": response.audio_url,
        "visual": None,
    })
    await websocket.send_json({
        "type": "resume",
        "from_turn": turn_index,
        "host_bridge_text": response.resume_text,
        "host_bridge_audio": response.resume_audio_url,
    })
