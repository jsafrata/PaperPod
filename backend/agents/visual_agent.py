"""Visual agent — visual selection + generation decisions."""

import logging
from typing import Optional
from sqlmodel import Session, select

from models.db import Visual
from services.visual_generator import generate_explainer_visual

logger = logging.getLogger(__name__)


class VisualAgent:
    """Decides when to show a visual and whether to generate a new one."""

    def __init__(self, paper_id: str):
        self.paper_id = paper_id

    async def get_or_generate_visual(
        self,
        topic: str,
        session_id: str,
        db: Session,
    ) -> Optional[dict]:
        """Try to find a relevant existing visual, or generate one."""
        # First check if any existing visual's caption matches
        visuals = db.exec(
            select(Visual).where(Visual.paper_id == self.paper_id)
        ).all()

        topic_lower = topic.lower()
        for v in visuals:
            if v.caption and topic_lower in v.caption.lower():
                return {
                    "id": v.id,
                    "image_url": v.image_url,
                    "caption": v.caption,
                    "provenance": v.provenance,
                }

        # No match — generate a new AI explainer visual
        return await generate_explainer_visual(
            paper_id=self.paper_id,
            topic=topic,
            session_id=session_id,
            db=db,
        )
