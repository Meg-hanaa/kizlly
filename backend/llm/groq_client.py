"""
llm/groq_client.py - Groq LLaMA 3.3 70B client for Kizlly.

Wraps the ``groq`` SDK with exponential-backoff retry logic, automatic
fallback to a smaller model on rate-limit errors (429), and a privacy log
that records every chunk sent to the Groq API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_FALLBACK_MODEL,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
    GROQ_MAX_RETRIES,
)

logger = logging.getLogger(__name__)

try:
    from groq import Groq
except ImportError:
    Groq = None  # type: ignore[misc,assignment]
    logger.warning("groq SDK is not installed. Run: pip install groq")


class GroqClient:
    """Chat-completion client for Groq-hosted LLaMA models.

    Features
    --------
    - Exponential backoff with jitter on transient errors.
    - Automatic model fallback on HTTP 429 (rate limit).
    - Built-in privacy log tracking every API call.

    Parameters
    ----------
    api_key : str, optional
        Groq API key.  Falls back to ``config.GROQ_API_KEY``.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key: str = api_key or GROQ_API_KEY
        if not self._api_key:
            raise ValueError(
                "Groq API key is not configured. Set GROQ_API_KEY in your "
                ".env file or pass it directly."
            )

        if Groq is None:
            raise RuntimeError(
                "groq SDK is not installed. Run: pip install groq"
            )

        self._client = Groq(api_key=self._api_key)
        self._model: str = GROQ_MODEL
        self._fallback_model: str = GROQ_FALLBACK_MODEL
        self._max_retries: int = GROQ_MAX_RETRIES

        # Privacy tracking
        self.privacy_log: List[Dict] = []

    # ------------------------------------------------------------------
    # Privacy helpers
    # ------------------------------------------------------------------

    def _log_call(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> None:
        """Record an API call for privacy auditing."""
        self.privacy_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "system_prompt_chars": len(system_prompt),
            "user_prompt_chars": len(user_prompt),
            "char_count": len(system_prompt) + len(user_prompt),
            "user_prompt_preview": user_prompt[:100],
        })

    def get_privacy_log(self) -> List[Dict]:
        """Return all recorded privacy log entries.

        Returns
        -------
        list[dict]
            Each entry contains ``timestamp``, ``model``,
            ``system_prompt_chars``, ``user_prompt_chars``,
            ``char_count``, and ``user_prompt_preview``.
        """
        return list(self.privacy_log)

    def clear_privacy_log(self) -> None:
        """Clear all privacy log entries."""
        self.privacy_log.clear()
        logger.info("Privacy log cleared.")

    # ------------------------------------------------------------------
    # Core chat method
    # ------------------------------------------------------------------

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = GROQ_TEMPERATURE,
        max_tokens: int = GROQ_MAX_TOKENS,
    ) -> str:
        """Send a chat-completion request to Groq.

        Parameters
        ----------
        system_prompt : str
            System-level instruction.
        user_prompt : str
            User message / clause text.
        temperature : float, optional
            Sampling temperature (default from config).
        max_tokens : int, optional
            Maximum response tokens (default from config).

        Returns
        -------
        str
            The assistant's reply text.

        Raises
        ------
        RuntimeError
            If all retries are exhausted.
        """
        current_model = self._model
        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            # Log the call *before* making it (privacy-first)
            self._log_call(current_model, system_prompt, user_prompt)

            try:
                response = self._client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                return content.strip()

            except Exception as exc:
                last_error = exc
                error_str = str(exc)

                # Rate-limit → switch to fallback model
                if "429" in error_str or "rate" in error_str.lower():
                    logger.warning(
                        "Rate limited on model '%s' (attempt %d/%d). "
                        "Switching to fallback '%s'.",
                        current_model,
                        attempt,
                        self._max_retries,
                        self._fallback_model,
                    )
                    current_model = self._fallback_model

                # Exponential backoff: 1s, 2s, 4s, 8s …
                backoff = min(2 ** (attempt - 1), 30)
                logger.warning(
                    "Groq API error (attempt %d/%d): %s — retrying in %ds.",
                    attempt,
                    self._max_retries,
                    error_str[:200],
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(
            f"Groq API call failed after {self._max_retries} retries. "
            f"Last error: {last_error}"
        )
