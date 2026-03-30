"""Text chunking with section awareness and overlap."""

from dataclasses import dataclass


@dataclass
class TextChunk:
    text: str
    section_id: str | None
    section_title: str
    chunk_index: int
    visual_id: str | None = None  # if this chunk is a figure caption


def chunk_paper(
    sections: list[dict],
    captions: list[dict] | None = None,
    max_tokens: int = 350,
    overlap_tokens: int = 50,
) -> list[TextChunk]:
    """Chunk paper text into retrieval-sized pieces.

    Args:
        sections: list of {"id", "title", "text"} dicts
        captions: optional list of {"visual_id", "caption", "section_id"} dicts
        max_tokens: approximate max tokens per chunk (~4 chars per token)
        overlap_tokens: token overlap between consecutive chunks
    """
    chunks: list[TextChunk] = []
    global_idx = 0
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    for section in sections:
        section_id = section.get("id")
        section_title = section.get("title", "")
        text = section.get("text", "").strip()

        if not text:
            continue

        # Split into paragraphs first
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        current_chunk = ""
        for para in paragraphs:
            # If adding this paragraph exceeds max, flush current chunk
            if current_chunk and len(current_chunk) + len(para) + 1 > max_chars:
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    section_id=section_id,
                    section_title=section_title,
                    chunk_index=global_idx,
                ))
                global_idx += 1

                # Keep overlap from end of current chunk
                if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                    current_chunk = current_chunk[-overlap_chars:]
                else:
                    current_chunk = ""

            current_chunk += ("\n" if current_chunk else "") + para

        # Flush remaining text
        if current_chunk.strip():
            chunks.append(TextChunk(
                text=current_chunk.strip(),
                section_id=section_id,
                section_title=section_title,
                chunk_index=global_idx,
            ))
            global_idx += 1

    # Add figure captions as separate small chunks
    if captions:
        for cap in captions:
            caption_text = cap.get("caption", "").strip()
            if caption_text:
                chunks.append(TextChunk(
                    text=caption_text,
                    section_id=cap.get("section_id"),
                    section_title="Figure/Table Caption",
                    chunk_index=global_idx,
                    visual_id=cap.get("visual_id"),
                ))
                global_idx += 1

    return chunks
