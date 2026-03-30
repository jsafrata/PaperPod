"""Retrieval service with Gemini embeddings. Supports pgvector (Postgres) and keyword fallback (SQLite)."""

import json
import logging
import os
from typing import Optional

from google import genai
from sqlmodel import Session, select, text as sql_text

from config import settings
from models.db import Chunk

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768

_use_pgvector = bool(os.environ.get("DATABASE_URL", ""))


def _get_genai_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts using Gemini."""
    if not texts:
        return []

    client = _get_genai_client()
    embeddings = []

    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
        )
        for emb in result.embeddings:
            embeddings.append(emb.values)

    return embeddings


async def generate_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text."""
    client = _get_genai_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
    )
    return result.embeddings[0].values


async def store_chunks_with_embeddings(
    chunks: list[dict],
    db: Session,
) -> list[Chunk]:
    """Store chunks in the database, with embeddings if pgvector is available."""
    if not chunks:
        return []

    db_chunks = []

    if _use_pgvector:
        # Generate and store real embeddings
        texts = [c["text"] for c in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = await generate_embeddings(texts)

        for chunk_data, embedding in zip(chunks, embeddings):
            db_chunk = Chunk(
                paper_id=chunk_data["paper_id"],
                section_id=chunk_data.get("section_id"),
                text=chunk_data["text"],
                chunk_index=chunk_data["chunk_index"],
                visual_id=chunk_data.get("visual_id"),
                embedding=embedding,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)
    else:
        # SQLite: store chunks without embeddings
        logger.info(f"Storing {len(chunks)} chunks (no embeddings — SQLite mode)")
        for chunk_data in chunks:
            db_chunk = Chunk(
                paper_id=chunk_data["paper_id"],
                section_id=chunk_data.get("section_id"),
                text=chunk_data["text"],
                chunk_index=chunk_data["chunk_index"],
                visual_id=chunk_data.get("visual_id"),
                embedding=None,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

    db.commit()
    logger.info(f"Stored {len(db_chunks)} chunks")
    return db_chunks


async def search_chunks(
    paper_id: str,
    query: str,
    db: Session,
    top_k: int = 5,
) -> list[dict]:
    """Search for relevant chunks. Uses pgvector if available, else keyword match."""

    if _use_pgvector:
        return await _search_pgvector(paper_id, query, db, top_k)
    else:
        return _search_keyword(paper_id, query, db, top_k)


async def _search_pgvector(paper_id: str, query: str, db: Session, top_k: int) -> list[dict]:
    """Vector similarity search via pgvector."""
    query_embedding = await generate_single_embedding(query)

    results = db.exec(
        sql_text("""
            SELECT id, text, section_id, chunk_index, visual_id,
                   1 - (embedding <=> :query_vec::vector) as score
            FROM chunk
            WHERE paper_id = :paper_id
            ORDER BY embedding <=> :query_vec::vector
            LIMIT :top_k
        """),
        params={
            "query_vec": str(query_embedding),
            "paper_id": paper_id,
            "top_k": top_k,
        },
    ).all()

    return [
        {
            "id": r[0], "text": r[1], "section_id": r[2],
            "chunk_index": r[3], "visual_id": r[4],
            "score": float(r[5]) if r[5] else 0.0,
        }
        for r in results
    ]


def _search_keyword(paper_id: str, query: str, db: Session, top_k: int) -> list[dict]:
    """Simple keyword-based fallback for SQLite (no vector search)."""
    all_chunks = db.exec(
        select(Chunk).where(Chunk.paper_id == paper_id)
    ).all()

    if not all_chunks:
        return []

    # Score by keyword overlap
    query_words = set(query.lower().split())
    scored = []
    for chunk in all_chunks:
        chunk_words = set(chunk.text.lower().split())
        overlap = len(query_words & chunk_words)
        scored.append((chunk, overlap))

    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        {
            "id": c.id, "text": c.text, "section_id": c.section_id,
            "chunk_index": c.chunk_index, "visual_id": c.visual_id,
            "score": float(s),
        }
        for c, s in scored[:top_k]
    ]
