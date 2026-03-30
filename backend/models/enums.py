from enum import Enum


class SessionMode(str, Enum):
    PROCESSING = "processing"
    PLAYING = "playing"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    QUIZ = "quiz"
    RECAP = "recap"


class SpeakerRole(str, Enum):
    HOST = "host"
    EXPERT = "expert"
    SKEPTIC = "skeptic"


class VisualType(str, Enum):
    FIGURE = "figure"
    TABLE = "table"
    AI_GENERATED = "ai_generated"


class Provenance(str, Enum):
    FROM_PAPER = "from_paper"
    AI_GENERATED = "ai_generated"


class PaperStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
