RECAP_SYSTEM_PROMPT = """You are generating an end-of-session recap for an interactive research paper podcast. The user has been listening to a discussion and may have asked questions and taken quizzes."""

RECAP_BEGINNER_INSTRUCTION = "Write the recap in simple, accessible language. Use analogies and plain terms. Flashcard definitions should be jargon-free."
RECAP_TECHNICAL_INSTRUCTION = "Write the recap at a graduate/researcher level. Use precise technical language, reference specific metrics and methods. Flashcard definitions can assume domain knowledge."


RECAP_USER_PROMPT = """Generate a session recap based on the following data.

**Paper Knowledge Pack:**
{knowledge_pack_summary}

**User Q&A History:**
{qa_history}

**Quiz Results:**
{quiz_results}

**Weak Concepts:** {weak_concepts}

{difficulty_instruction}

Generate a JSON object with:
{{
  "takeaways": ["3 key takeaways — the most important things to remember"],
  "limitations": ["2 major limitations of this paper"],
  "flashcards": [
    {{"front": "question or term", "back": "answer or definition"}},
    ... (3 flashcards)
  ],
  "weak_concepts": ["concepts the user struggled with based on quiz results"]
}}

Focus the flashcards on concepts the user found difficult. If no quiz data exists, use the paper's core concepts.

Return ONLY valid JSON."""
