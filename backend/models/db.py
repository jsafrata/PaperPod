import os
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Column, Text
from sqlalchemy import text as sa_text

from .enums import PaperStatus, SessionMode, SpeakerRole, VisualType, Provenance

# pgvector only works with Postgres — use Text column for SQLite fallback
_use_pgvector = bool(os.environ.get("DATABASE_URL", ""))
if _use_pgvector:
    try:
        from pgvector.sqlalchemy import Vector
        _embedding_column = Column(Vector(768))
    except Exception:
        _embedding_column = Column(Text, nullable=True)
else:
    _embedding_column = Column(Text, nullable=True)  # store as JSON string in SQLite


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Paper(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    title: str = ""
    authors: Optional[str] = None  # JSON list stored as string
    source_url: Optional[str] = None
    pdf_storage_path: str = ""  # path in Supabase Storage
    status: str = Field(default=PaperStatus.PROCESSING)
    knowledge_pack_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    processing_step: str = "reading_paper"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Section(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    paper_id: str = Field(foreign_key="paper.id")
    title: str = ""
    text: str = Field(default="", sa_column=Column(Text))
    order_index: int = 0
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class Visual(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    paper_id: str = Field(foreign_key="paper.id")
    section_id: Optional[str] = Field(default=None, foreign_key="section.id")
    type: str = Field(default=VisualType.FIGURE)
    image_url: str = ""  # Supabase Storage public URL
    storage_path: str = ""  # path in Supabase Storage
    caption: Optional[str] = None
    page_number: Optional[int] = None
    provenance: str = Field(default=Provenance.FROM_PAPER)


class Chunk(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    paper_id: str = Field(foreign_key="paper.id")
    section_id: Optional[str] = Field(default=None, foreign_key="section.id")
    text: str = Field(default="", sa_column=Column(Text))
    chunk_index: int = 0
    visual_id: Optional[str] = None
    embedding: Optional[str] = Field(default=None, sa_column=_embedding_column)


class Session(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    paper_id: str = Field(foreign_key="paper.id")
    mode: str = Field(default=SessionMode.PROCESSING)
    difficulty: str = "beginner"
    focus: Optional[str] = None
    current_turn_index: int = 0
    weak_concepts_json: Optional[str] = None  # JSON list
    style_directive: Optional[str] = None  # Active restyle directive (e.g. "make it simpler")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PodcastTurn(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    turn_index: int = 0
    speaker: str = Field(default=SpeakerRole.HOST)
    text: str = Field(default="", sa_column=Column(Text))
    section: str = ""
    audio_url: Optional[str] = None  # Supabase Storage public URL
    audio_storage_path: Optional[str] = None
    visual_id: Optional[str] = None


class QAEntry(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    question: str = Field(default="", sa_column=Column(Text))
    answer: str = Field(default="", sa_column=Column(Text))
    speaker: str = ""
    turn_index_at: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QuizAttempt(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    session_id: str = Field(foreign_key="session.id")
    question_text: str = Field(default="", sa_column=Column(Text))
    user_answer: str = ""
    correct: bool = False
    concept: str = ""
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
