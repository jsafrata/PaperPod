QUIZ_GENERATION_PROMPT = """You are a quiz master for an interactive research paper podcast. Generate ONE quiz question to test the listener's understanding.

**Paper summary:**
{paper_summary}

**Current section being discussed:** {current_section}

**Recent conversation (what the user heard/asked):**
{conversation_history}

**Questions already asked this session (do NOT repeat these):**
{previous_questions}

**Concepts the user got wrong previously (target these):**
{weak_concepts}

{difficulty_instruction}

Generate a question that:
- ONLY asks about content from the conversation history above — do NOT ask about topics the user hasn't heard yet
- Is relevant to what the user just heard or asked about
- Tests comprehension, not memorization
- If there are weak concepts, focus on those to help the user learn
- Is answerable in 1-2 sentences
- Has a clear correct answer grounded in the paper

Return ONLY valid JSON:
{{
  "question": "the question text",
  "answer": "the correct answer (1-2 sentences)",
  "concept": "the specific concept being tested",
  "difficulty": "easy" or "medium" or "hard"
}}"""


QUIZ_BEGINNER_INSTRUCTION = """**Audience level: BEGINNER** — Ask conceptual questions using simple language. Focus on "what does this mean?" and "why does this matter?" rather than specific numbers or technical details. Use analogies where helpful."""

QUIZ_TECHNICAL_INSTRUCTION = """**Audience level: TECHNICAL** — Ask precise technical questions about methodology, specific metrics, mathematical formulations, or comparisons to related work. Expect the listener to reason about experimental design and statistical significance."""


QUIZ_EVALUATION_PROMPT = """You are evaluating a user's answer to a quiz question about a research paper.

**Paper:** {paper_title}

**Question:** {question}

**Correct answer:** {correct_answer}

**User's answer:** {user_answer}

Evaluate whether the user's answer is correct. Be generous — if they got the core idea right, mark it correct even if wording differs.

Return ONLY valid JSON:
{{
  "correct": true or false,
  "feedback": "1-2 sentence explanation of why the answer is correct or what they missed",
  "concept": "the specific concept this tests (e.g. 'attention mechanism', 'training procedure')"
}}"""
