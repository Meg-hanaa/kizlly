"""
ingestion/pdf_parser.py - PDF text extraction for Kizlly.

Uses PyMuPDF (fitz) as the primary parser and pdfplumber as a fallback
for table-heavy documents.  Preserves [PAGE N] markers so downstream
clause-citation logic can reference source pages.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional imports – graceful degradation
# ---------------------------------------------------------------------------
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logger.warning("PyMuPDF (fitz) is not installed; PDF parsing will rely on pdfplumber.")

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber is not installed; table-heavy fallback unavailable.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Remove common headers, footers, and page-number artefacts.

    Patterns removed:
      • Standalone page numbers (e.g. ``- 3 -``, ``Page 3 of 10``)
      • Repeated header / footer boilerplate (lines that appear verbatim
        at the top/bottom of many pages are not removed here – that requires
        cross-page deduplication, handled at a higher level).
      • Excessive whitespace / blank lines.
    """
    # "Page X of Y" / "Page X"
    text = re.sub(r"(?i)page\s+\d+\s*(of\s+\d+)?", "", text)
    # Centred page numbers: "- 3 -" or "— 3 —"
    text = re.sub(r"[—–-]\s*\d+\s*[—–-]", "", text)
    # Standalone line that is just a number (page number artefact)
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Primary parser – PyMuPDF (fitz)
# ---------------------------------------------------------------------------

def _parse_with_fitz(file_path: str) -> Dict:
    """Extract text using PyMuPDF."""
    doc = fitz.open(file_path)  # type: ignore[union-attr]
    pages: list[str] = []
    metadata: dict = {}

    try:
        metadata = {
            k: v for k, v in (doc.metadata or {}).items() if v
        }
    except Exception:
        pass

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw = page.get_text("text") or ""
        cleaned = _clean_text(raw)
        if cleaned:
            pages.append(f"[PAGE {page_num + 1}]\n{cleaned}")

    doc.close()
    full_text = "\n\n".join(pages)
    return {
        "text": full_text,
        "pages": len(pages),
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Fallback parser – pdfplumber (better for tables)
# ---------------------------------------------------------------------------

def _parse_with_pdfplumber(file_path: str) -> Dict:
    """Extract text (including tables) using pdfplumber."""
    pages: list[str] = []
    metadata: dict = {}

    with pdfplumber.open(file_path) as pdf:  # type: ignore[union-attr]
        metadata = {k: v for k, v in (pdf.metadata or {}).items() if v}

        for page_num, page in enumerate(pdf.pages, start=1):
            parts: list[str] = []

            # Regular text
            raw = page.extract_text() or ""
            cleaned = _clean_text(raw)
            if cleaned:
                parts.append(cleaned)

            # Tables → flattened rows
            try:
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        cells = [str(c).strip() for c in row if c]
                        if cells:
                            parts.append(" | ".join(cells))
            except Exception:
                pass  # table extraction is best-effort

            if parts:
                pages.append(f"[PAGE {page_num}]\n" + "\n".join(parts))

    full_text = "\n\n".join(pages)
    return {
        "text": full_text,
        "pages": len(pages),
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_pdf(file_path: str) -> Dict:
    """Parse a PDF file and return structured text with metadata.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the PDF file.

    Returns
    -------
    dict
        ``{"text": str, "pages": int, "metadata": dict}``

    Raises
    ------
    FileNotFoundError
        If *file_path* does not exist.
    RuntimeError
        If neither parser is available or both fail.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    errors: list[str] = []

    # 1. Try PyMuPDF
    if fitz is not None:
        try:
            result = _parse_with_fitz(file_path)
            if result["text"]:
                logger.info("Parsed %s with PyMuPDF (%d pages).", file_path, result["pages"])
                return result
            logger.warning("PyMuPDF returned empty text for %s; falling back.", file_path)
        except Exception as exc:
            errors.append(f"PyMuPDF: {exc}")
            logger.warning("PyMuPDF failed for %s: %s", file_path, exc)

    # 2. Fallback to pdfplumber
    if pdfplumber is not None:
        try:
            result = _parse_with_pdfplumber(file_path)
            if result["text"]:
                logger.info("Parsed %s with pdfplumber (%d pages).", file_path, result["pages"])
                return result
            errors.append("pdfplumber: returned empty text")
        except Exception as exc:
            errors.append(f"pdfplumber: {exc}")
            logger.warning("pdfplumber failed for %s: %s", file_path, exc)

    # 3. Neither worked
    if fitz is None and pdfplumber is None:
        raise RuntimeError(
            "No PDF parsing library available. Install PyMuPDF or pdfplumber."
        )

    raise RuntimeError(
        f"All PDF parsers failed for {file_path}: {'; '.join(errors)}"
    )
