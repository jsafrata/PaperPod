from typing import Optional
from pydantic import BaseModel


# --- Paper ---

class PaperUploadResponse(BaseModel):
    paper_id: str
    status: str


class ArxivRequest(BaseModel):
    arxiv_url: str
    difficulty: str = "beginner"
    length: str = "standard"


class ProcessingStep(BaseModel):
    name: str
    status: str  # "pending" | "running" | "done"


class PaperStatusResponse(BaseModel):
    paper_id: str
    status: str
    title: str
    steps: list[ProcessingStep]
    session_id: Optional[str] = None  # Auto-created session ID (available during generating_voices)
    summary: Optional[str] = None


# --- Session ---

class SessionCreateRequest(BaseModel):
    paper_id: str
    difficulty: str = "beginner"
    focus: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    paper_id: str
    mode: str
    difficulty: str
    paper_title: str
    current_turn_index: int = 0
    total_turns: int = 0


# --- Podcast ---

class TurnResponse(BaseModel):
    index: int
    speaker: str
    text: str
    audio_url: Optional[str]
    visual_id: Optional[str]
    section: str


class PodcastTurnsResponse(BaseModel):
    session_id: str
    turns: list[TurnResponse]


# --- Visuals ---

class VisualResponse(BaseModel):
    id: str
    type: str
    image_url: str
    caption: Optional[str]
    page_number: Optional[int]
    provenance: str


# --- Interaction (WebSocket) ---

class InterruptRequest(BaseModel):
    question: str
    current_turn_index: int


class InterruptResponse(BaseModel):
    speaker: str
    text: str
    audio_url: Optional[str]
    visual: Optional[VisualResponse]


# --- Quiz ---

class QuizStartRequest(BaseModel):
    section: Optional[str] = None


class QuizQuestion(BaseModel):
    question_id: str
    text: str
    section: str


class QuizAnswerRequest(BaseModel):
    question_id: str
    answer: str


class QuizResult(BaseModel):
    correct: bool
    feedback: str
    weak_concepts: list[str]


# --- Recap ---

class Flashcard(BaseModel):
    front: str
    back: str


class RecapResponse(BaseModel):
    takeaways: list[str]
    limitations: list[str]
    flashcards: list[Flashcard]
    weak_concepts: list[str]
