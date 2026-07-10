"""
llm/risk_analyzer.py - Contract risk analysis orchestration for Kizlly.

Uses ``GroqClient`` to analyse individual clauses for legal risks,
detect contradictions between adjacent clause pairs, and produce
structured output compatible with the ``RiskFlag`` / ``ContradictionFlag``
models.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Dict, List, Optional, Tuple

from llm.groq_client import GroqClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_RISK_SYSTEM_PROMPT = (
    "You are a legal contract risk analyst. Analyze this clause for risks. "
    "Return JSON with: "
    "risk_type (specific risk name), "
    "category (one of: Liability, Termination, Indemnification, IP, "
    "Confidentiality, Payment, Renewal, Governing Law, Data Privacy, "
    "Force Majeure, Non-Compete, Other), "
    "severity (Critical/High/Medium/Low), "
    "explanation (1-2 sentences), "
    "confidence (0.0-1.0). "
    "If no risk found, set risk_type to 'None' and severity to 'Low'. "
    "Return ONLY valid JSON, no markdown fences or extra text."
)

_CONTRADICTION_SYSTEM_PROMPT = (
    "You are a legal contract analyst. You are given two clauses from the "
    "same contract. Determine if they contradict each other. "
    "Return JSON with: "
    "contradicts (true/false), "
    "explanation (1-2 sentences describing the contradiction or why they "
    "are consistent), "
    "severity (Critical/High/Medium/Low). "
    "Return ONLY valid JSON, no markdown fences or extra text."
)

# Minimum characters for a chunk to be worth analysing
_MIN_CHUNK_LENGTH = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_response(raw: str) -> Dict:
    """Best-effort parse of LLM JSON output.

    Strips markdown fences, trailing commas, and other common artefacts
    before parsing.
    """
    cleaned = raw.strip()
    # Remove ```json ... ``` wrappers
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Drop first and last lines if they are fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON: %s", cleaned[:200])
        return {
            "risk_type": "Parse Error",
            "category": "Other",
            "severity": "Low",
            "explanation": f"Could not parse LLM response: {cleaned[:200]}",
            "confidence": 0.0,
        }


# ---------------------------------------------------------------------------
# RiskAnalyzer
# ---------------------------------------------------------------------------

class RiskAnalyzer:
    """Orchestrates clause-level risk analysis and contradiction detection.

    Parameters
    ----------
    groq_client : GroqClient, optional
        Pre-configured client.  A new one is created if not supplied.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        self.groq_client = groq_client or GroqClient()

    # ------------------------------------------------------------------
    # Single-clause analysis
    # ------------------------------------------------------------------

    def analyze_clause(self, clause_text: str) -> Dict:
        """Analyse a single clause for legal risks.

        Parameters
        ----------
        clause_text : str
            The clause text to analyse.

        Returns
        -------
        dict
            Keys: ``risk_type``, ``category``, ``severity``,
            ``explanation``, ``confidence``.
        """
        try:
            raw = self.groq_client.chat(
                system_prompt=_RISK_SYSTEM_PROMPT,
                user_prompt=clause_text,
            )
            result = _parse_json_response(raw)

            # Normalise keys (LLM may use varying casing)
            return {
                "risk_type": result.get("risk_type", "Unknown"),
                "category": result.get("category", "Other"),
                "severity": result.get("severity", "Medium"),
                "explanation": result.get("explanation", ""),
                "confidence": float(result.get("confidence", 0.5)),
            }

        except Exception as exc:
            logger.error("analyze_clause failed: %s", exc)
            return {
                "risk_type": "Analysis Error",
                "category": "Other",
                "severity": "Low",
                "explanation": f"Analysis failed: {exc}",
                "confidence": 0.0,
            }

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------

    def detect_contradiction(
        self, clause_a: str, clause_b: str
    ) -> Dict:
        """Check whether two clauses contradict each other.

        Parameters
        ----------
        clause_a : str
            First clause text.
        clause_b : str
            Second clause text.

        Returns
        -------
        dict
            Keys: ``contradicts`` (bool), ``explanation`` (str),
            ``severity`` (str).
        """
        user_prompt = (
            f"Clause A:\n{clause_a}\n\n"
            f"Clause B:\n{clause_b}"
        )

        try:
            raw = self.groq_client.chat(
                system_prompt=_CONTRADICTION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            result = _parse_json_response(raw)

            contradicts = result.get("contradicts", False)
            if isinstance(contradicts, str):
                contradicts = contradicts.lower() in ("true", "yes", "1")

            return {
                "contradicts": bool(contradicts),
                "explanation": result.get("explanation", ""),
                "severity": result.get("severity", "Medium"),
            }

        except Exception as exc:
            logger.error("detect_contradiction failed: %s", exc)
            return {
                "contradicts": False,
                "explanation": f"Detection failed: {exc}",
                "severity": "Low",
            }

    # ------------------------------------------------------------------
    # Full-contract analysis
    # ------------------------------------------------------------------

    def analyze_contract(
        self, chunks: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Analyse all chunks in a contract for risks and contradictions.

        Parameters
        ----------
        chunks : list[dict]
            Chunk dicts produced by ``ingestion.chunker.chunk_text``.  Each
            must have at least ``id`` and ``text`` keys.

        Returns
        -------
        tuple[list[dict], list[dict]]
            ``(risk_flags, contradictions)``

            - **risk_flags** – one ``RiskFlag``-compatible dict per
              analysed chunk (only for chunks where a risk was found).
            - **contradictions** – one ``ContradictionFlag``-compatible
              dict per detected contradiction between adjacent chunks.
        """
        risk_flags: List[Dict] = []
        contradictions: List[Dict] = []

        # Filter out empty / very short chunks
        valid_chunks = [
            c for c in chunks
            if c.get("text", "").strip() and len(c.get("text", "")) >= _MIN_CHUNK_LENGTH
        ]

        if not valid_chunks:
            logger.warning("No valid chunks to analyse.")
            return risk_flags, contradictions

        logger.info("Analysing %d chunks for risks …", len(valid_chunks))

        # ----- Risk analysis -----
        for chunk in valid_chunks:
            analysis = self.analyze_clause(chunk["text"])

            # Only flag if a real risk was found
            if analysis["risk_type"] not in ("None", "Analysis Error", "Parse Error"):
                risk_flags.append({
                    "id": str(uuid.uuid4())[:8],
                    "clause_id": chunk.get("id", ""),
                    "clause_text": chunk["text"],
                    "risk_type": analysis["risk_type"],
                    "category": analysis["category"],
                    "severity": analysis["severity"],
                    "explanation": analysis["explanation"],
                    "ai_confidence": analysis["confidence"],
                })

        logger.info("Found %d risk flags.", len(risk_flags))

        # ----- Contradiction detection (adjacent pairs) -----
        logger.info("Checking %d adjacent pairs for contradictions …", max(len(valid_chunks) - 1, 0))
        for i in range(len(valid_chunks) - 1):
            a = valid_chunks[i]
            b = valid_chunks[i + 1]

            result = self.detect_contradiction(a["text"], b["text"])

            if result["contradicts"]:
                contradictions.append({
                    "clause_a_id": a.get("id", ""),
                    "clause_a_text": a["text"],
                    "clause_b_id": b.get("id", ""),
                    "clause_b_text": b["text"],
                    "explanation": result["explanation"],
                    "severity": result["severity"],
                })

        logger.info("Found %d contradictions.", len(contradictions))
        return risk_flags, contradictions
