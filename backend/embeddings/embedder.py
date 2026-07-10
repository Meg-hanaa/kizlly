"""
embeddings/embedder.py - Sentence-transformer embeddings for Kizlly.

Provides a thin wrapper around ``sentence_transformers.SentenceTransformer``
with lazy model loading so the import is fast and the heavy model is only
materialised when the first embedding request arrives.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

from config import EMBEDDING_MODEL, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class Embedder:
    """Generate normalised sentence embeddings using a SentenceTransformer model.

    Parameters
    ----------
    model_name : str, optional
        HuggingFace model identifier (default: ``config.EMBEDDING_MODEL``).

    Attributes
    ----------
    model_name : str
        Model identifier used for loading.
    dimension : int
        Expected embedding dimension (from ``config.EMBEDDING_DIMENSION``).
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name: str = model_name or EMBEDDING_MODEL
        self.dimension: int = EMBEDDING_DIMENSION
        self._model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Lazy loader
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the SentenceTransformer model on first use."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from exc

        logger.info("Loading embedding model '%s' …", self.model_name)
        self._model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into normalised embedding vectors.

        Parameters
        ----------
        texts : list[str]
            Texts to embed.

        Returns
        -------
        np.ndarray
            Array of shape ``(len(texts), self.dimension)`` with L2-normalised
            vectors (suitable for inner-product / cosine search).
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        self._load_model()

        try:
            embeddings: np.ndarray = self._model.encode(  # type: ignore[union-attr]
                texts,
                batch_size=64,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            raise RuntimeError(f"Embedding failed: {exc}") from exc

        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string.

        Parameters
        ----------
        query : str
            The query text.

        Returns
        -------
        np.ndarray
            1-D array of shape ``(self.dimension,)``.
        """
        if not query or not query.strip():
            raise ValueError("Query text must not be empty.")

        result = self.embed([query])
        return result[0]
