import asyncio
import json
import logging
import threading

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session

from deps import get_db, engine
from models.schemas import PaperUploadResponse, ArxivRequest, PaperStatusResponse, ProcessingStep
from models.db import Paper
from models.enums import PaperStatus
from services.paper_ingestion import ingest_paper
from utils.arxiv import parse_arxiv_id, fetch_arxiv_pdf, fetch_arxiv_metadata

logger = logging.getLogger(__name__)

router = APIRouter(tags=["papers"])


def _run_ingestion_in_thread(paper_id: str, pdf_bytes: bytes):
    """Run the full async ingestion pipeline in a new thread with its own event loop."""
    def _target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with Session(engine) as db:
                loop.run_until_complete(ingest_paper(paper_id, pdf_bytes, db))
        except Exception as e:
            logger.error(f"Ingestion failed for {paper_id}: {e}", exc_info=True)
            # Mark as failed
            try:
                with Session(engine) as db:
                    paper = db.get(Paper, paper_id)
                    if paper:
                        paper.status = PaperStatus.FAILED
                        db.commit()
            except Exception:
                pass
        finally:
            loop.close()

    t = threading.Thread(target=_target, daemon=True)
    t.start()


@router.post("/papers/upload", response_model=PaperUploadResponse)
async def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a PDF and start processing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    paper = Paper(
        title=file.filename.replace(".pdf", ""),
        pdf_storage_path="",
        status=PaperStatus.PROCESSING,
        processing_step="reading_paper",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    _run_ingestion_in_thread(paper.id, pdf_bytes)

    return PaperUploadResponse(paper_id=paper.id, status=paper.status)


@router.post("/papers/arxiv", response_model=PaperUploadResponse)
async def upload_arxiv(
    req: ArxivRequest,
    db: Session = Depends(get_db),
):
    """Accept an arXiv URL and start processing."""
    try:
        arxiv_id = parse_arxiv_id(req.arxiv_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid arXiv URL or ID")

    # Fetch metadata (quick, with timeout so we don't block)
    try:
        metadata = await asyncio.wait_for(fetch_arxiv_metadata(arxiv_id), timeout=5)
    except Exception:
        metadata = {"title": f"arXiv:{arxiv_id}", "authors": []}

    paper = Paper(
        title=metadata["title"],
        authors=json.dumps(metadata["authors"]),
        source_url=req.arxiv_url,
        pdf_storage_path="",
        status=PaperStatus.PROCESSING,
        processing_step="reading_paper",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # Download PDF and ingest in a background thread
    def _download_and_ingest():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pdf_bytes = loop.run_until_complete(fetch_arxiv_pdf(arxiv_id))
            logger.info(f"Downloaded arXiv PDF: {len(pdf_bytes)} bytes")
            with Session(engine) as db2:
                loop.run_until_complete(ingest_paper(paper.id, pdf_bytes, db2, difficulty=req.difficulty, length=req.length))
        except Exception as e:
            logger.error(f"arXiv ingestion failed: {e}", exc_info=True)
            try:
                with Session(engine) as db2:
                    p = db2.get(Paper, paper.id)
                    if p:
                        p.status = PaperStatus.FAILED
                        db2.commit()
            except Exception:
                pass
        finally:
            loop.close()

    t = threading.Thread(target=_download_and_ingest, daemon=True)
    t.start()

    return PaperUploadResponse(paper_id=paper.id, status=paper.status)


@router.get("/papers/{paper_id}", response_model=dict)
async def get_paper(paper_id: str, db: Session = Depends(get_db)):
    """Get paper metadata."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": json.loads(paper.authors) if paper.authors else [],
        "source_url": paper.source_url,
        "status": paper.status,
        "created_at": paper.created_at.isoformat(),
    }


@router.get("/papers/{paper_id}/knowledge-pack")
async def get_knowledge_pack(paper_id: str, db: Session = Depends(get_db)):
    """Get the knowledge pack for a paper."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.knowledge_pack_json:
        raise HTTPException(status_code=404, detail="Knowledge pack not yet generated")
    return json.loads(paper.knowledge_pack_json)


@router.get("/papers/{paper_id}/status", response_model=PaperStatusResponse)
async def get_paper_status(paper_id: str, db: Session = Depends(get_db)):
    """Get processing status for a paper."""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    all_steps = [
        "reading_paper",
        "extracting_visuals",
        "building_explanations",
        "writing_script",
        "generating_voices",
        "preparing_quiz",
    ]
    step_labels = {
        "reading_paper": "Reading paper",
        "extracting_visuals": "Extracting visuals",
        "building_explanations": "Building explanations",
        "writing_script": "Writing script",
        "generating_voices": "Generating voices",
        "preparing_quiz": "Preparing quiz",
    }

    # Extract session_id and clean step name (step can be "generating_voices:session_id")
    session_id = None
    current_step = paper.processing_step or ""
    if ":" in current_step:
        current_step, session_id = current_step.split(":", 1)

    if paper.status == PaperStatus.READY:
        steps = [ProcessingStep(name=step_labels[s], status="done") for s in all_steps]
    elif paper.status == PaperStatus.FAILED:
        steps = [ProcessingStep(name=step_labels[s], status="done") for s in all_steps]
        steps[-1] = ProcessingStep(name="Processing failed", status="running")
    else:
        steps = []
        current_found = False
        for step in all_steps:
            if step == current_step:
                steps.append(ProcessingStep(name=step_labels[step], status="running"))
                current_found = True
            elif not current_found:
                steps.append(ProcessingStep(name=step_labels[step], status="done"))
            else:
                steps.append(ProcessingStep(name=step_labels[step], status="pending"))

    return PaperStatusResponse(
        paper_id=paper.id,
        status=paper.status,
        title=paper.title,
        steps=steps,
        session_id=session_id,
        summary=paper.summary,
    )
