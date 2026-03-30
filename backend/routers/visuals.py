from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from deps import get_db
from models.schemas import VisualResponse
from models.db import Visual

router = APIRouter(tags=["visuals"])


@router.get("/visuals/{paper_id}", response_model=list[VisualResponse])
async def get_visuals(paper_id: str, db: Session = Depends(get_db)):
    """Get all extracted visuals for a paper."""
    visuals = db.exec(
        select(Visual).where(Visual.paper_id == paper_id)
    ).all()

    return [
        VisualResponse(
            id=v.id,
            type=v.type,
            image_url=v.image_url,
            caption=v.caption,
            page_number=v.page_number,
            provenance=v.provenance,
        )
        for v in visuals
    ]
