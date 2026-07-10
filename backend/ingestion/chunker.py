"""
ingestion/chunker.py - Legal-contract text chunking for Kizlly.

Splits full-contract text into small, overlapping chunks suitable for
embedding and risk analysis.  Prefers *semantic* boundaries (section /
article / clause headings) and falls back to a sliding-window strategy
when no structural markers are present.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Dict, List, Optional

from config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNK_SENTENCES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Section / Article / Clause heading (case-insensitive)
_SECTION_RE = re.compile(
    r"(?:Section|Article|Clause|SECTION|ARTICLE|CLAUSE)\s+\d+",
    re.IGNORECASE,
)

# [PAGE N] markers injected by the parsers
_PAGE_MARKER_RE = re.compile(r"\[PAGE\s+(\d+)\]")

# Sentence boundary – period / question-mark / exclamation followed by space
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_page(text: str, offset: int, page_map: List[tuple]) -> Optional[int]:
    """Return the page number for a given character *offset*.

    Parameters
    ----------
    text : str
        Not used directly – kept for potential future refinement.
    offset : int
        Character offset within the full document.
    page_map : list[tuple]
        Sorted list of ``(offset, page_number)`` from ``[PAGE N]`` markers.
    """
    page: Optional[int] = None
    for marker_offset, page_num in page_map:
        if marker_offset <= offset:
            page = page_num
        else:
            break
    return page


def _detect_section(text: str) -> Optional[str]:
    """Return the first Section/Article/Clause heading found in *text*."""
    match = _SECTION_RE.search(text)
    return match.group(0).strip() if match else None


def _build_page_map(text: str) -> List[tuple]:
    """Build a sorted list of ``(char_offset, page_number)`` pairs."""
    return [
        (m.start(), int(m.group(1)))
        for m in _PAGE_MARKER_RE.finditer(text)
    ]


def _cap_sentences(text: str, max_sentences: int) -> str:
    """Truncate *text* to at most *max_sentences* sentences."""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    if len(sentences) <= max_sentences:
        return text
    return " ".join(sentences[:max_sentences])


# ---------------------------------------------------------------------------
# Semantic chunking (preferred)
# ---------------------------------------------------------------------------

def _semantic_chunk(
    text: str,
    chunk_size: int,
    overlap: int,
    max_sentences: int,
    page_map: List[tuple],
) -> List[Dict]:
    """Split *text* on section / article / clause boundaries."""
    # Find split positions
    boundaries = [m.start() for m in _SECTION_RE.finditer(text)]
    if not boundaries:
        return []  # no section markers → caller should use sliding window

    # Ensure we capture text before the first heading
    if boundaries[0] != 0:
        boundaries.insert(0, 0)

    chunks: List[Dict] = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        raw_chunk = text[start:end].strip()

        if not raw_chunk:
            continue

        # Sub-chunk large sections with sliding window
        if len(raw_chunk) > chunk_size:
            sub_chunks = _sliding_window_chunk(
                raw_chunk,
                chunk_size,
                overlap,
                max_sentences,
                page_map,
                base_offset=start,
            )
            chunks.extend(sub_chunks)
        else:
            capped = _cap_sentences(raw_chunk, max_sentences)
            chunks.append({
                "id": str(uuid.uuid4())[:8],
                "text": capped,
                "page": _detect_page(text, start, page_map),
                "section": _detect_section(raw_chunk),
                "char_offset": start,
                "char_count": len(capped),
            })

    return chunks


# ---------------------------------------------------------------------------
# Sliding-window chunking (fallback)
# ---------------------------------------------------------------------------

def _sliding_window_chunk(
    text: str,
    chunk_size: int,
    overlap: int,
    max_sentences: int,
    page_map: List[tuple],
    base_offset: int = 0,
) -> List[Dict]:
    """Split *text* into overlapping fixed-size windows."""
    chunks: List[Dict] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        raw_chunk = text[start:end].strip()

        if not raw_chunk:
            start += chunk_size - overlap
            continue

        capped = _cap_sentences(raw_chunk, max_sentences)
        abs_offset = base_offset + start

        chunks.append({
            "id": str(uuid.uuid4())[:8],
            "text": capped,
            "page": _detect_page(text, abs_offset, page_map),
            "section": _detect_section(raw_chunk),
            "char_offset": abs_offset,
            "char_count": len(capped),
        })

        # Advance with overlap
        step = chunk_size - overlap
        if step <= 0:
            step = chunk_size  # safety: avoid infinite loop
        start += step

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[Dict]:
    """Split contract *text* into structured chunks.

    Parameters
    ----------
    text : str
        Full contract text, optionally containing ``[PAGE N]`` markers.
    chunk_size : int, optional
        Target character count per chunk (default from ``config.CHUNK_SIZE``).
    overlap : int, optional
        Character overlap between consecutive chunks (default from
        ``config.CHUNK_OVERLAP``).

    Returns
    -------
    list[dict]
        Each dict contains:

        - **id** – short UUID
        - **text** – chunk text (≤ ``MAX_CHUNK_SENTENCES`` sentences)
        - **page** – source page number or ``None``
        - **section** – detected section heading or ``None``
        - **char_offset** – character offset in original text
        - **char_count** – length of the chunk text
    """
    if not text or not text.strip():
        logger.warning("chunk_text called with empty text.")
        return []

    page_map = _build_page_map(text)
    max_sentences = MAX_CHUNK_SENTENCES

    # 1. Attempt semantic chunking
    chunks = _semantic_chunk(text, chunk_size, overlap, max_sentences, page_map)

    if chunks:
        logger.info(
            "Semantic chunking produced %d chunks (avg %d chars).",
            len(chunks),
            sum(c["char_count"] for c in chunks) // max(len(chunks), 1),
        )
        return chunks

    # 2. Fallback to sliding window
    logger.info("No section markers found; falling back to sliding-window chunking.")
    chunks = _sliding_window_chunk(text, chunk_size, overlap, max_sentences, page_map)
    logger.info(
        "Sliding-window chunking produced %d chunks (avg %d chars).",
        len(chunks),
        sum(c["char_count"] for c in chunks) // max(len(chunks), 1),
    )
    return chunks
