"""Multi-speaker podcast script generation using Gemini."""

import json
import logging
from typing import Optional

from google import genai
from google.genai import types
from sqlmodel import Session, select

from config import settings
from models.db import Paper, Visual, PodcastTurn, Session as SessionModel
from prompts.script import (
    SCRIPT_SYSTEM_PROMPT,
    SCRIPT_USER_PROMPT,
    RESTYLE_SYSTEM_PROMPT,
    RESTYLE_USER_PROMPT,
    BEGINNER_SCRIPT_INSTRUCTION,
    TECHNICAL_SCRIPT_INSTRUCTION,
)

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3-flash-preview"


def _get_genai_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


LENGTH_CONFIG = {
    "quick": {"target": "8-12", "limit": 12},
    "standard": {"target": "18-22", "limit": 22},
    "deep": {"target": "25-30", "limit": 30},
}


async def generate_podcast_script(
    session_id: str,
    db: Session,
    length: str = "standard",
) -> list[dict]:
    """Generate a podcast script from the knowledge pack and store turns in DB.

    Returns list of turn dicts: [{speaker, section, text, visual_id}, ...]
    """
    session = db.get(SessionModel, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    paper = db.get(Paper, session.paper_id)
    if not paper or not paper.knowledge_pack_json:
        raise ValueError(f"Paper or knowledge pack not found for session {session_id}")

    knowledge_pack = json.loads(paper.knowledge_pack_json)

    # Get available figures
    visuals = db.exec(
        select(Visual).where(Visual.paper_id == paper.id)
    ).all()
    figures_info = [
        {
            "visual_id": v.id,
            "type": v.type,
            "caption": v.caption or "",
            "page_number": v.page_number,
        }
        for v in visuals
    ]

    # Build prompt
    difficulty_instruction = (
        BEGINNER_SCRIPT_INSTRUCTION if session.difficulty == "beginner"
        else TECHNICAL_SCRIPT_INSTRUCTION
    )
    length_cfg = LENGTH_CONFIG.get(length, LENGTH_CONFIG["standard"])
    user_prompt = SCRIPT_USER_PROMPT.format(
        knowledge_pack_json=json.dumps(knowledge_pack, indent=2),
        figures_json=json.dumps(figures_info, indent=2),
        difficulty_instruction=difficulty_instruction,
        target_turns=length_cfg["target"],
    )

    # Generate script
    client = _get_genai_client()
    logger.info(f"Generating podcast script for session {session_id}...")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=SCRIPT_SYSTEM_PROMPT,
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()
    turns = json.loads(raw_text)

    # Validate and store turns
    if not isinstance(turns, list):
        raise ValueError("Script generation did not return a list of turns")

    # Hard limit based on selected length
    max_turns = length_cfg["limit"]
    turns = turns[:max_turns]

    db_turns = []
    for i, turn in enumerate(turns):
        speaker = turn.get("speaker", "host")
        if speaker not in ("host", "expert", "skeptic"):
            speaker = "host"

        section = turn.get("section", "intro")
        text = turn.get("text", "")
        visual_id = turn.get("visual_id")

        # Validate visual_id exists
        if visual_id and not any(v.id == visual_id for v in visuals):
            visual_id = None

        db_turn = PodcastTurn(
            session_id=session_id,
            turn_index=i,
            speaker=speaker,
            text=text,
            section=section,
            visual_id=visual_id,
        )
        db.add(db_turn)
        db_turns.append(db_turn)

    db.commit()
    logger.info(f"Generated {len(db_turns)} podcast turns for session {session_id}")

    return [
        {
            "speaker": t.speaker,
            "section": t.section,
            "text": t.text,
            "visual_id": t.visual_id,
        }
        for t in db_turns
    ]


async def generate_restyled_script(
    session_id: str,
    db: Session,
    from_turn_index: int,
    style_directive: str,
    max_turns: Optional[int] = None,
) -> list[dict]:
    """Regenerate remaining podcast turns with a new style directive.

    Args:
        max_turns: If set, generate at most this many turns (for fast first-batch).

    Returns list of turn dicts (not persisted to DB -- caller handles that).
    """
    session = db.get(SessionModel, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    paper = db.get(Paper, session.paper_id)
    if not paper or not paper.knowledge_pack_json:
        raise ValueError(f"Paper or knowledge pack not found for session {session_id}")

    knowledge_pack = json.loads(paper.knowledge_pack_json)

    # Get available figures
    visuals = db.exec(
        select(Visual).where(Visual.paper_id == paper.id)
    ).all()
    figures_info = [
        {
            "visual_id": v.id,
            "type": v.type,
            "caption": v.caption or "",
            "page_number": v.page_number,
        }
        for v in visuals
    ]

    # Get preceding turns (already played, for continuity)
    all_turns = db.exec(
        select(PodcastTurn)
        .where(PodcastTurn.session_id == session_id)
        .order_by(PodcastTurn.turn_index)
    ).all()

    preceding_turns = [
        {"speaker": t.speaker, "section": t.section, "text": t.text}
        for t in all_turns
        if t.turn_index <= from_turn_index
    ]

    total_turns = len(all_turns)
    num_remaining = total_turns - from_turn_index - 1
    if max_turns is not None:
        num_remaining = min(num_remaining, max_turns)

    # Determine which sections still need coverage
    covered_sections = {t.section for t in all_turns if t.turn_index <= from_turn_index}
    all_sections = ["intro", "method", "results", "limitations"]
    remaining_sections = [s for s in all_sections if s not in covered_sections or s in {
        t.section for t in all_turns if t.turn_index > from_turn_index
    }]

    difficulty_instruction = (
        BEGINNER_SCRIPT_INSTRUCTION if session.difficulty == "beginner"
        else TECHNICAL_SCRIPT_INSTRUCTION
    )

    user_prompt = RESTYLE_USER_PROMPT.format(
        style_directive=style_directive,
        knowledge_pack_json=json.dumps(knowledge_pack, indent=2),
        figures_json=json.dumps(figures_info, indent=2),
        preceding_turns_json=json.dumps(preceding_turns, indent=2),
        remaining_sections=", ".join(remaining_sections) if remaining_sections else "wrap-up",
        num_remaining_turns=max(num_remaining, 3),
        difficulty_instruction=difficulty_instruction,
    )

    client = _get_genai_client()
    logger.info(f"Generating restyled script for session {session_id} (from turn {from_turn_index + 1}, style: {style_directive[:50]})")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=RESTYLE_SYSTEM_PROMPT,
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()
    turns = json.loads(raw_text)

    if not isinstance(turns, list):
        raise ValueError("Restyle script generation did not return a list of turns")

    # Validate and normalize turns
    valid_visual_ids = {v.id for v in visuals}
    result = []
    for turn in turns[:num_remaining]:  # Truncate to original count
        speaker = turn.get("speaker", "host")
        if speaker not in ("host", "expert", "skeptic"):
            speaker = "host"

        visual_id = turn.get("visual_id")
        if visual_id and visual_id not in valid_visual_ids:
            visual_id = None

        result.append({
            "speaker": speaker,
            "section": turn.get("section", "intro"),
            "text": turn.get("text", ""),
            "visual_id": visual_id,
        })

    logger.info(f"Restyled script generated: {len(result)} turns")
    return result
