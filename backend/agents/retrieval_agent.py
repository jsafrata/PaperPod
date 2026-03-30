"""Retrieval + translation agent — fetches chunks, simplifies/deepens."""

import logging
from sqlmodel import Session

from services.retrieval import search_chunks

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """Retrieves relevant paper chunks for grounding live answers."""

    def __init__(self, paper_id: str):
        self.paper_id = paper_id

    async def retrieve(self, query: str, db: Session, top_k: int = 5) -> list[dict]:
        """Fetch the most relevant chunks for a question."""
        try:
            chunks = await search_chunks(self.paper_id, query, db, top_k=top_k)
            logger.info(f"Retrieved {len(chunks)} chunks for query: {query[:50]}...")
            return chunks
        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")
            return []
