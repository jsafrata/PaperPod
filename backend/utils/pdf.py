"""PyMuPDF helpers for text extraction, section detection, and figure extraction."""

import io
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from PIL import Image


@dataclass
class ExtractedSection:
    title: str
    text: str
    order_index: int
    page_start: int
    page_end: int


@dataclass
class ExtractedFigure:
    image_bytes: bytes
    caption: str
    page_number: int
    figure_label: str  # e.g. "Figure 1", "Table 2"
    content_type: str = "image/png"


# Common section header patterns
SECTION_PATTERNS = [
    # "1 Introduction", "2. Methods", "3.1 Dataset" — number followed by a word starting with uppercase
    re.compile(r"^\s*\d+\.?\d*\.?\s+[A-Z][a-zA-Z]"),
    # Roman numerals: "I. Introduction", "IV Results"
    re.compile(r"^\s*(I{1,3}V?|VI{0,3}|IX|X)\.?\s+[A-Z]"),
    # Named sections without numbering
    re.compile(r"^\s*(Abstract|Introduction|Related Work|Background|Methodology|Methods?|Approach|Experiments?|Results?|Discussion|Conclusions?|Limitations|Acknowledgm?ents?|References|Appendix)\s*$", re.IGNORECASE),
]

FIGURE_CAPTION_PATTERN = re.compile(
    r"(Figure|Fig\.|Table)\s+(\d+)", re.IGNORECASE
)


def extract_text_and_sections(pdf_bytes: bytes) -> tuple[str, list[ExtractedSection]]:
    """Extract full text and detect sections from a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text_parts: list[str] = []
    raw_blocks: list[dict] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict", sort=True)["blocks"]
        for block in blocks:
            if block.get("type") != 0:  # text blocks only
                continue
            for line in block.get("lines", []):
                line_text = ""
                is_bold = False
                font_size = 0
                for span in line.get("spans", []):
                    line_text += span["text"]
                    if "bold" in span.get("font", "").lower() or "Bold" in span.get("font", ""):
                        is_bold = True
                    font_size = max(font_size, span.get("size", 0))
                line_text = line_text.strip()
                if line_text:
                    raw_blocks.append({
                        "text": line_text,
                        "page": page_num,
                        "is_bold": is_bold,
                        "font_size": font_size,
                    })
                    full_text_parts.append(line_text)

    doc.close()
    full_text = "\n".join(full_text_parts)

    # Detect sections
    sections = _detect_sections(raw_blocks)

    # If no sections detected, create one big section
    if not sections:
        max_page = raw_blocks[-1]["page"] if raw_blocks else 0
        sections = [ExtractedSection(
            title="Full Paper",
            text=full_text,
            order_index=0,
            page_start=0,
            page_end=max_page,
        )]

    return full_text, sections


def _detect_sections(blocks: list[dict]) -> list[ExtractedSection]:
    """Detect section boundaries from text blocks."""
    if not blocks:
        return []

    # Find median font size to identify headers (larger than median)
    font_sizes = [b["font_size"] for b in blocks if b["font_size"] > 0]
    if not font_sizes:
        return []
    median_size = sorted(font_sizes)[len(font_sizes) // 2]

    section_starts: list[tuple[int, str]] = []  # (block_index, title)

    for i, block in enumerate(blocks):
        text = block["text"]
        # Check regex patterns
        for pattern in SECTION_PATTERNS:
            if pattern.match(text) and 3 < len(text) < 80:
                section_starts.append((i, text))
                break
        else:
            # Check if it's a bold header with larger font
            if (block["is_bold"] and
                block["font_size"] > median_size * 1.1 and
                len(text) < 80 and
                len(text) > 2):
                section_starts.append((i, text))

    # Build sections from detected starts
    sections: list[ExtractedSection] = []
    for idx, (start_block_idx, title) in enumerate(section_starts):
        end_block_idx = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(blocks)
        section_blocks = blocks[start_block_idx + 1:end_block_idx]  # skip the header itself
        section_text = "\n".join(b["text"] for b in section_blocks)
        page_start = blocks[start_block_idx]["page"]
        page_end = section_blocks[-1]["page"] if section_blocks else page_start

        sections.append(ExtractedSection(
            title=title.strip(),
            text=section_text.strip(),
            order_index=idx,
            page_start=page_start,
            page_end=page_end,
        ))

    return sections


def extract_figures(pdf_bytes: bytes) -> list[ExtractedFigure]:
    """Extract embedded images and their captions from a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    figures: list[ExtractedFigure] = []
    seen_xrefs: set[int] = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")

        images = page.get_images(full=True)
        for img_info in images:
            xref = img_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image["image"]
                # Skip very small images (likely icons/logos)
                img = Image.open(io.BytesIO(image_bytes))
                w, h = img.size
                if w < 100 or h < 100:
                    continue

                # Convert to PNG
                png_buffer = io.BytesIO()
                img.save(png_buffer, format="PNG")
                png_bytes = png_buffer.getvalue()

                # Try to find a caption near this image
                caption, label = _find_caption(page_text, len(figures) + 1)

                figures.append(ExtractedFigure(
                    image_bytes=png_bytes,
                    caption=caption,
                    page_number=page_num,
                    figure_label=label,
                    content_type="image/png",
                ))
            except Exception:
                continue

    doc.close()
    return figures


def _find_caption(page_text: str, figure_index: int) -> tuple[str, str]:
    """Find a figure/table caption in the page text."""
    matches = list(FIGURE_CAPTION_PATTERN.finditer(page_text))
    for match in matches:
        label = match.group(0)
        # Get text after the label up to end of line or next 200 chars
        start = match.start()
        end = min(start + 300, len(page_text))
        snippet = page_text[start:end]
        # Take first line or sentence
        caption_lines = snippet.split("\n")
        caption = caption_lines[0].strip()
        if len(caption_lines) > 1 and len(caption_lines[1].strip()) > 10:
            caption += " " + caption_lines[1].strip()
        return caption, label

    return f"Figure {figure_index}", f"Figure {figure_index}"


def get_page_count(pdf_bytes: bytes) -> int:
    """Get the number of pages in a PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = len(doc)
    doc.close()
    return count
