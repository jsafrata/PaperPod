"""Quick paper summary generation using Gemini."""

import json
import logging

from google import genai
from google.genai import types
from config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3-flash-preview"

SUMMARY_PROMPT = """You are a research paper summarizer. Given the text of a research paper, produce a structured JSON summary.

Return ONLY valid JSON with this exact structure:
{
  "one_liner": "A single sentence describing what this paper does",
  "key_points": ["point 1", "point 2", "point 3"],
  "method": "One sentence describing the core method or approach",
  "finding": "One sentence describing the most important result",
  "why_it_matters": "One sentence on the broader significance"
}

Rules:
- Keep each field concise (1 sentence max, key_points 3-4 items of ~10 words each)
- Be accessible to a general audience
- No markdown, no formatting — just plain text values"""


async def generate_quick_summary(full_text: str, paper_title: str = "") -> str:
    """Generate a structured summary from extracted paper text.

    Returns a JSON string. Called early in the pipeline so the user
    sees something useful while the rest of processing continues.
    """
    client = genai.Client(api_key=settings.gemini_api_key)

    # Use first ~8K chars — keeps it fast and leaves room for output tokens
    text_excerpt = full_text[:8_000]
    if len(full_text) > 8_000:
        text_excerpt += "\n\n[Text truncated for summary...]"

    user_msg = f"Paper title: {paper_title}\n\nPaper text:\n{text_excerpt}"

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_msg)],
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=SUMMARY_PROMPT,
            temperature=0.3,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )

    # Validate it's proper JSON
    raw = response.text.strip()
    json.loads(raw)  # raises if invalid
    return raw
