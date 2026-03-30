"""Knowledge pack generation using Gemini structured output."""

import json
import logging
import io
import tempfile
import os
from typing import Optional

from google import genai
from google.genai import types

from config import settings
from prompts.knowledge_pack import (
    KNOWLEDGE_PACK_SYSTEM_PROMPT,
    KNOWLEDGE_PACK_USER_PROMPT,
    BEGINNER_INSTRUCTION,
    TECHNICAL_INSTRUCTION,
)

logger = logging.getLogger(__name__)

# Gemini model for document understanding
GEMINI_MODEL = "gemini-3-flash-preview"


def _get_genai_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def generate_knowledge_pack(
    pdf_bytes: bytes,
    difficulty: str = "beginner",
    paper_title: str = "",
) -> dict:
    """Generate a knowledge pack from a PDF using Gemini.

    Uploads the PDF to Gemini Files API and uses document understanding
    with structured output to produce the knowledge pack.
    """
    client = _get_genai_client()

    # Write PDF to temp file for upload
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        # Upload to Gemini Files API
        logger.info(f"Uploading PDF to Gemini Files API ({len(pdf_bytes)} bytes)...")
        uploaded_file = client.files.upload(file=tmp_path)
        logger.info(f"Uploaded as: {uploaded_file.name}")

        # Build prompt
        difficulty_instruction = (
            BEGINNER_INSTRUCTION if difficulty == "beginner" else TECHNICAL_INSTRUCTION
        )
        user_prompt = KNOWLEDGE_PACK_USER_PROMPT.format(
            difficulty_instruction=difficulty_instruction,
        )

        # Generate with structured output
        logger.info("Generating knowledge pack...")
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type="application/pdf",
                        ),
                        types.Part.from_text(text=user_prompt),
                    ],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=KNOWLEDGE_PACK_SYSTEM_PROMPT,
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )

        # Parse the JSON response
        raw_text = response.text.strip()
        knowledge_pack = json.loads(raw_text)

        # Ensure title is set
        if not knowledge_pack.get("title") and paper_title:
            knowledge_pack["title"] = paper_title

        logger.info(
            f"Knowledge pack generated: {len(knowledge_pack.get('sections', []))} sections, "
            f"{len(knowledge_pack.get('quiz_bank', []))} quiz questions"
        )

        # Clean up uploaded file
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

        return knowledge_pack

    finally:
        os.unlink(tmp_path)


async def generate_knowledge_pack_from_text(
    full_text: str,
    difficulty: str = "beginner",
    paper_title: str = "",
) -> dict:
    """Fallback: generate knowledge pack from extracted text (no PDF upload).

    Used when Gemini Files API is unavailable or for testing.
    """
    client = _get_genai_client()

    difficulty_instruction = (
        BEGINNER_INSTRUCTION if difficulty == "beginner" else TECHNICAL_INSTRUCTION
    )
    user_prompt = KNOWLEDGE_PACK_USER_PROMPT.format(
        difficulty_instruction=difficulty_instruction,
    )

    # Truncate text if too long (Gemini has context limits)
    max_chars = 100_000
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n\n[Text truncated...]"

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f"Here is the research paper text:\n\n{full_text}\n\n---\n\n{user_prompt}"
                    ),
                ],
            ),
        ],
        config=types.GenerateContentConfig(
            system_instruction=KNOWLEDGE_PACK_SYSTEM_PROMPT,
            temperature=0.3,
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()
    knowledge_pack = json.loads(raw_text)

    if not knowledge_pack.get("title") and paper_title:
        knowledge_pack["title"] = paper_title

    return knowledge_pack
