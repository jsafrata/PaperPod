"""Paper ingestion pipeline: PDF → sections + figures → knowledge pack → script + TTS → playback.

Optimized: script + TTS start as soon as knowledge pack is ready.
Embeddings deferred to background after playback starts.
"""

import asyncio
import json
import logging
import threading
from sqlmodel import Session, select

from models.db import Paper, Section, Visual, Session as SessionModel
from models.enums import PaperStatus, SessionMode, VisualType, Provenance
from storage.supabase import upload_file
from utils.pdf import extract_text_and_sections, extract_figures
from services.chunker import chunk_paper
from services.retrieval import store_chunks_with_embeddings
from services.knowledge_pack import generate_knowledge_pack, generate_knowledge_pack_from_text
from services.summary import generate_quick_summary
from services.script_generator import generate_podcast_script
from services.tts import generate_all_turn_audio, generate_remaining_turn_audio
from services.visual_generator import generate_visuals_for_session, generate_remaining_visuals

logger = logging.getLogger(__name__)


async def ingest_paper(paper_id: str, pdf_bytes: bytes, db: Session, difficulty: str = "beginner", length: str = "standard") -> Paper:
    """Run the full ingestion pipeline for a paper.

    Steps:
    1. Upload PDF to Supabase Storage
    2. Extract text and sections
    3. Extract figures
    4. Generate knowledge pack (Gemini)
    5. Chunk text + generate embeddings (Gemini + pgvector)
    """
    paper = db.get(Paper, paper_id)
    if not paper:
        raise ValueError(f"Paper {paper_id} not found")

    try:
        # --- Step 1: Upload PDF to Supabase Storage ---
        _update_step(paper, "reading_paper", db)
        storage_path = f"{paper_id}/paper.pdf"
        try:
            upload_file("papers", storage_path, pdf_bytes, "application/pdf")
            paper.pdf_storage_path = storage_path
        except Exception as e:
            logger.warning(f"Supabase upload failed (continuing): {e}")
            paper.pdf_storage_path = "local"
        db.commit()

        # --- Step 2: Extract text and sections ---
        full_text, extracted_sections = extract_text_and_sections(pdf_bytes)
        logger.info(f"Extracted {len(extracted_sections)} sections from paper {paper_id}")

        db_sections = []
        for es in extracted_sections:
            section = Section(
                paper_id=paper_id,
                title=es.title,
                text=es.text,
                order_index=es.order_index,
                page_start=es.page_start,
                page_end=es.page_end,
            )
            db.add(section)
            db_sections.append(section)
        db.commit()
        # Refresh to get IDs
        for s in db_sections:
            db.refresh(s)

        # --- Step 2b: Generate quick summary ---
        try:
            summary = await generate_quick_summary(full_text, paper.title)
            paper.summary = summary
            db.commit()
            logger.info(f"Quick summary generated for paper {paper_id}")
        except Exception as e:
            logger.warning(f"Quick summary generation failed (non-fatal): {e}")

        # --- Step 3: Extract figures ---
        _update_step(paper, "extracting_visuals", db)
        extracted_figures = extract_figures(pdf_bytes)
        logger.info(f"Extracted {len(extracted_figures)} figures from paper {paper_id}")

        db_visuals = []
        for i, ef in enumerate(extracted_figures):
            visual_storage_path = f"{paper_id}/{i}.png"
            try:
                image_url = upload_file("visuals", visual_storage_path, ef.image_bytes, ef.content_type)
            except Exception as e:
                logger.warning(f"Failed to upload figure {i}: {e}")
                image_url = ""

            section_id = _find_section_for_page(db, paper_id, ef.page_number)

            visual = Visual(
                paper_id=paper_id,
                section_id=section_id,
                type=VisualType.FIGURE if "table" not in ef.figure_label.lower() else VisualType.TABLE,
                image_url=image_url,
                storage_path=visual_storage_path,
                caption=ef.caption,
                page_number=ef.page_number,
                provenance=Provenance.FROM_PAPER,
            )
            db.add(visual)
            db_visuals.append(visual)
        db.commit()
        for v in db_visuals:
            db.refresh(v)

        # --- Step 4: Generate knowledge pack ---
        _update_step(paper, "building_explanations", db)
        try:
            knowledge_pack = await generate_knowledge_pack(
                pdf_bytes=pdf_bytes,
                difficulty=difficulty,
                paper_title=paper.title,
            )
        except Exception as e:
            logger.warning(f"PDF-based knowledge pack failed, falling back to text: {e}")
            knowledge_pack = await generate_knowledge_pack_from_text(
                full_text=full_text,
                difficulty=difficulty,
                paper_title=paper.title,
            )

        # Update paper with knowledge pack and title from Gemini
        paper.knowledge_pack_json = json.dumps(knowledge_pack)
        if knowledge_pack.get("title"):
            paper.title = knowledge_pack["title"]
        db.commit()
        logger.info(f"Knowledge pack generated for paper {paper_id}")

        # --- Step 5: Create session + generate script ---
        _update_step(paper, "writing_script", db)

        # Create session immediately
        session = SessionModel(
            paper_id=paper_id,
            difficulty=difficulty,
            mode=SessionMode.PROCESSING,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Auto-created session {session.id} for paper {paper_id}")

        # Store session_id on the paper for frontend to find
        paper.processing_step = f"writing_script:{session.id}"
        db.commit()
        logger.info(f"Auto-created session {session.id}")

        # Generate podcast script
        await generate_podcast_script(session.id, db, length=length)
        logger.info(f"Script generated for session {session.id}")

        # --- Step 6: TTS generation ---
        paper.processing_step = f"generating_voices:{session.id}"
        db.commit()

        # TTS all turns (true parallelism via run_in_executor)
        success_count = await generate_all_turn_audio(session.id, db)
        logger.info(f"TTS complete: {success_count} turns")

        # --- Step 7: Generate AI visuals (only 4, one per section — fast) ---
        paper.processing_step = f"preparing_quiz:{session.id}"
        db.commit()

        remaining_visuals = []
        try:
            visual_count, remaining_visuals = await generate_visuals_for_session(session.id, paper_id, db, max_blocking=3)
            logger.info(f"Generated {visual_count} AI visuals (blocking)")
        except Exception as e:
            logger.warning(f"Visual generation failed (non-fatal): {e}")

        # Mark session as PLAYING — don't wait for last visual
        session.mode = SessionMode.PLAYING
        db.commit()
        logger.info(f"Session {session.id} ready for playback")

        # Mark paper as ready
        paper.status = PaperStatus.READY
        paper.processing_step = "done"
        db.commit()

        # --- Background: generate embeddings (deferred, not blocking playback) ---
        def _background_embeddings():
            """Generate embeddings in background thread after playback starts."""
            from deps import engine as _engine
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                with Session(_engine) as bg_db:
                    section_dicts = [
                        {"id": s.id, "title": s.title, "text": s.text}
                        for s in bg_db.exec(select(Section).where(Section.paper_id == paper_id)).all()
                    ]
                    caption_dicts = [
                        {"visual_id": v.id, "caption": v.caption or "", "section_id": v.section_id}
                        for v in bg_db.exec(select(Visual).where(Visual.paper_id == paper_id)).all()
                        if v.caption
                    ]
                    text_chunks = chunk_paper(section_dicts, caption_dicts)
                    chunk_dicts = [
                        {"text": tc.text, "paper_id": paper_id, "section_id": tc.section_id,
                         "chunk_index": tc.chunk_index, "visual_id": tc.visual_id}
                        for tc in text_chunks
                    ]
                    loop.run_until_complete(store_chunks_with_embeddings(chunk_dicts, bg_db))
                    logger.info(f"Background embeddings complete for paper {paper_id}")
            except Exception as e:
                logger.warning(f"Background embeddings failed (non-fatal): {e}")
            finally:
                loop.close()

        threading.Thread(target=_background_embeddings, daemon=True).start()

        # Generate remaining visuals in background
        if remaining_visuals:
            def _background_remaining_visuals():
                from deps import engine as _engine
                bg_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(bg_loop)
                try:
                    with Session(_engine) as bg_db:
                        bg_loop.run_until_complete(
                            generate_remaining_visuals(remaining_visuals, paper_id, bg_db)
                        )
                except Exception as e:
                    logger.warning(f"Background remaining visuals failed: {e}")
                finally:
                    bg_loop.close()
            threading.Thread(target=_background_remaining_visuals, daemon=True).start()

        logger.info(f"Paper {paper_id} ingestion complete")
        return paper

    except Exception as e:
        logger.error(f"Paper ingestion failed for {paper_id}: {e}", exc_info=True)
        paper.status = PaperStatus.FAILED
        db.commit()
        raise


def _update_step(paper: Paper, step: str, db: Session):
    """Update the current processing step."""
    paper.processing_step = step
    db.commit()


def _find_section_for_page(db: Session, paper_id: str, page_number: int) -> str | None:
    """Find the section that contains the given page number."""
    sections = db.exec(
        select(Section)
        .where(Section.paper_id == paper_id)
        .where(Section.page_start <= page_number)
        .where(Section.page_end >= page_number)
    ).all()
    return sections[0].id if sections else None
