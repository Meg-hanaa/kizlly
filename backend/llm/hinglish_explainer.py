"""
llm/hinglish_explainer.py - Hinglish clause explanation generator for Kizlly.

Translates complex legal clauses into simple Hinglish (Hindi-English mix)
so that non-legal users in India can quickly understand contract terms.
"""

from __future__ import annotations

import logging
from typing import Optional

from llm.groq_client import GroqClient

logger = logging.getLogger(__name__)

_HINGLISH_SYSTEM_PROMPT = (
    "You are a legal assistant who explains complex legal clauses in simple "
    "Hinglish (Hindi-English mix commonly spoken in India). "
    "Rules: "
    "Use simple everyday Hinglish, "
    "keep legal terms in English but explain in Hindi, "
    "use daily life examples, "
    "maintain accuracy while simplifying. "
    "Keep response under 100 words."
)


class HinglishExplainer:
    """Generate plain-Hinglish explanations of legal clauses.

    Parameters
    ----------
    groq_client : GroqClient, optional
        Pre-configured client.  A new one is created if not supplied.
    """

    def __init__(self, groq_client: Optional[GroqClient] = None) -> None:
        self.groq_client = groq_client or GroqClient()

    def explain(self, clause_text: str) -> str:
        """Return a Hinglish explanation of *clause_text*.

        Parameters
        ----------
        clause_text : str
            The legal clause to explain.

        Returns
        -------
        str
            Plain-text Hinglish explanation (≤ ~100 words).
            On failure, returns a user-friendly error message.
        """
        if not clause_text or not clause_text.strip():
            return "Koi clause text nahi diya gaya."

        try:
            explanation = self.groq_client.chat(
                system_prompt=_HINGLISH_SYSTEM_PROMPT,
                user_prompt=clause_text,
            )
            return explanation

        except Exception as exc:
            logger.error("Hinglish explanation failed: %s", exc)
            return (
                "Maaf kijiye, is clause ko samjhane mein error aa gaya. "
                "Thodi der baad dobara try karein."
            )
