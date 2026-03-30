"""AI explainer visual generation via Gemini native image generation."""

import asyncio
import logging
from typing import Optional

from google import genai
from google.genai import types
from sqlmodel import Session, select

from config import settings
from models.db import Visual, PodcastTurn
from models.enums import VisualType, Provenance
from storage.supabase import upload_file

logger = logging.getLogger(__name__)

IMAGE_MODEL = "gemini-2.5-flash-image"
MAX_CONCURRENT = 3


async def generate_visuals_for_session(
    session_id: str,
    paper_id: str,
    db: Session,
    max_blocking: int = 3,
) -> tuple[int, list]:
    """Generate one AI visual per section for turns without paper figures.

    Generates up to `max_blocking` images synchronously.
    Returns (count_generated, remaining_sections) where remaining_sections
    can be passed to generate the rest in background.
    """
    turns = db.exec(
        select(PodcastTurn)
        .where(PodcastTurn.session_id == session_id)
        .order_by(PodcastTurn.turn_index)
    ).all()

    # Group turns without visuals by section
    sections_needing_visuals: dict[str, list[PodcastTurn]] = {}
    for t in turns:
        if not t.visual_id:
            sections_needing_visuals.setdefault(t.section, []).append(t)

    if not sections_needing_visuals:
        logger.info("All turns already have visuals")
        return 0

    all_sections = list(sections_needing_visuals.items())
    blocking = all_sections[:max_blocking]
    remaining = all_sections[max_blocking:]

    logger.info(f"Generating {len(blocking)} visuals now, {len(remaining)} in background...")

    async def _generate_for_section(section: str, section_turns: list[PodcastTurn]) -> bool:
        combined_text = " ".join(t.text for t in section_turns[:3])
        visual = await _generate_single_visual(
            paper_id=paper_id,
            turn_text=combined_text,
            turn_index=section_turns[0].turn_index,
            speaker=section_turns[0].speaker,
            section=section,
            db=db,
        )
        if visual:
            for t in section_turns:
                t.visual_id = visual.id
            db.commit()
            return True
        return False

    # Generate first batch (blocking)
    results = await asyncio.gather(
        *[_generate_for_section(sec, t_list) for sec, t_list in blocking],
        return_exceptions=True,
    )
    count = sum(1 for r in results if r is True)
    logger.info(f"Generated {count} visuals (blocking)")

    return count, remaining


async def generate_remaining_visuals(
    remaining_sections: list,
    paper_id: str,
    db: Session,
) -> int:
    """Generate remaining section visuals (called in background)."""
    if not remaining_sections:
        return 0

    count = 0
    for section, section_turns in remaining_sections:
        combined_text = " ".join(t.text for t in section_turns[:3])
        visual = await _generate_single_visual(
            paper_id=paper_id,
            turn_text=combined_text,
            turn_index=section_turns[0].turn_index,
            speaker=section_turns[0].speaker,
            section=section,
            db=db,
        )
        if visual:
            for t in section_turns:
                t.visual_id = visual.id
            db.commit()
            count += 1

    logger.info(f"Background visuals: generated {count}")
    return count


async def _generate_single_visual(
    paper_id: str,
    turn_text: str,
    turn_index: int,
    speaker: str,
    section: str,
    db: Session,
) -> Optional[Visual]:
    """Generate one AI visual for a turn using Gemini native image generation."""
    client = genai.Client(api_key=settings.gemini_api_key)

    section_labels = {
        "intro": "introduction and overview",
        "method": "methodology and architecture",
        "results": "results and performance",
        "limitations": "limitations and future work",
    }
    section_label = section_labels.get(section, section)

    prompt = (
        f"Generate a clean, simple educational diagram or illustration for the '{section_label}' section of a research paper podcast. "
        f"Content being discussed: {turn_text[:400]}. "
        f"Style: minimal, informative, light background, clear labels, no watermarks. "
        f"Focus on visual concepts, flowcharts, architecture diagrams, or comparison charts — not decorative art."
    )

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        ))

        # Extract image from response
        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_data = part.inline_data.data
                break

        if not image_data:
            logger.warning(f"No image generated for turn {turn_index}")
            return None

        # Create visual record
        visual = Visual(
            paper_id=paper_id,
            type=VisualType.FIGURE,
            caption=f"{turn_text[:100]}...",
            provenance=Provenance.AI_GENERATED,
        )
        db.add(visual)
        db.flush()

        storage_path = f"{paper_id}/ai_{turn_index}.png"
        try:
            image_url = upload_file("visuals", storage_path, image_data, "image/png")
            visual.image_url = image_url
            visual.storage_path = storage_path
        except Exception as e:
            logger.warning(f"Failed to upload AI visual for turn {turn_index}: {e}")
            visual.image_url = ""

        db.commit()
        db.refresh(visual)
        return visual

    except Exception as e:
        logger.warning(f"AI visual generation failed for turn {turn_index}: {e}")
        return None
