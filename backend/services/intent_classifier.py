"""Classify user messages as questions or style/restyle directives using keyword heuristic."""


RESTYLE_KEYWORDS = [
    # Simplification
    "simpler", "simplify", "simple", "easier",
    "like i'm 5", "eli5", "like a child", "for a beginner",
    "less jargon", "dumb it down", "layman",
    # Complexity increase
    "technical", "more detail", "advanced", "deeper level",
    "more jargon", "more rigorous",
    # Focus shifts
    "focus on", "more about",
    "math", "equations", "intuition",
    "practical", "theoretical",
    "more examples", "more analogies",
    # Pacing
    "shorter", "longer", "faster", "slower", "concise", "brief",
    # Explicit style words
    "tone", "style", "language", "level",
]


def classify_intent(message: str) -> tuple[str, str]:
    """Classify a user message as a restyle directive or a question.

    Returns:
        ("restyle", original_message) if the message is a style preference.
        ("question", original_message) if the message is a question.
    """
    lower = message.lower().strip()
    for kw in RESTYLE_KEYWORDS:
        if kw in lower:
            return ("restyle", message)
    return ("question", message)
