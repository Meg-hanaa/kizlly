"""
vectorstore/faiss_store.py - FAISS vector index for Kizlly.

Manages a flat inner-product index (``IndexFlatIP``) that stores normalised
vectors, making inner product equivalent to cosine similarity.  A parallel
metadata list tracks chunk text, page, section, and contract_id for each
vector.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from config import EMBEDDING_DIMENSION, FAISS_DIR

logger = logging.getLogger(__name__)

try:
    import faiss
except ImportError:
    faiss = None  # type: ignore[assignment]
    logger.warning("faiss-cpu is not installed; FAISSStore will not work.")


class FAISSStore:
    """Thin wrapper around a FAISS ``IndexFlatIP`` index.

    Parameters
    ----------
    dimension : int, optional
        Dimensionality of the embedding vectors (default:
        ``config.EMBEDDING_DIMENSION``).

    Attributes
    ----------
    index : faiss.IndexFlatIP
        The underlying FAISS index.
    documents : list[dict]
        Parallel metadata list; one dict per vector.
    """

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        if faiss is None:
            raise RuntimeError(
                "faiss-cpu is not installed. Run: pip install faiss-cpu"
            )

        self.dimension: int = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.documents: List[Dict] = []

    # ------------------------------------------------------------------
    # Add vectors
    # ------------------------------------------------------------------

    def add(self, embeddings: np.ndarray, documents: List[Dict]) -> None:
        """Add vectors and their associated metadata to the index.

        Parameters
        ----------
        embeddings : np.ndarray
            Array of shape ``(n, self.dimension)`` with **normalised** vectors.
        documents : list[dict]
            One metadata dict per vector.  Expected keys (all optional):
            ``text``, ``page``, ``section``, ``contract_id``, ``chunk_id``.

        Raises
        ------
        ValueError
            If *embeddings* and *documents* have mismatched lengths or
            wrong dimensionality.
        """
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Expected embeddings of shape (n, {self.dimension}), "
                f"got {embeddings.shape}."
            )
        if len(embeddings) != len(documents):
            raise ValueError(
                f"Embeddings count ({len(embeddings)}) != documents count "
                f"({len(documents)})."
            )

        self.index.add(embeddings.astype(np.float32))
        self.documents.extend(documents)
        logger.info("Added %d vectors (total: %d).", len(documents), self.index.ntotal)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> List[Dict]:
        """Retrieve the *top_k* most similar documents.

        Parameters
        ----------
        query_embedding : np.ndarray
            1-D or 2-D normalised query vector.
        top_k : int, optional
            Number of results to return (default ``5``).

        Returns
        -------
        list[dict]
            Each dict is a copy of the stored metadata enriched with a
            ``score`` key (cosine similarity in ``[0, 1]``).
        """
        if self.index.ntotal == 0:
            logger.warning("Search called on empty index.")
            return []

        # Ensure 2-D
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        query_embedding = query_embedding.astype(np.float32)
        effective_k = min(top_k, self.index.ntotal)

        distances, indices = self.index.search(query_embedding, effective_k)

        results: List[Dict] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue  # FAISS uses -1 for empty slots
            doc = dict(self.documents[idx])  # shallow copy
            doc["score"] = float(score)
            results.append(doc)

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None) -> None:
        """Persist the index and metadata to disk.

        Parameters
        ----------
        path : str, optional
            Directory to save into (default: ``config.FAISS_DIR``).
        """
        save_dir = Path(path) if path else Path(FAISS_DIR)
        save_dir.mkdir(parents=True, exist_ok=True)

        index_path = save_dir / "index.faiss"
        meta_path = save_dir / "metadata.json"

        faiss.write_index(self.index, str(index_path))

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, default=str)

        logger.info(
            "FAISS index saved to %s (%d vectors).", save_dir, self.index.ntotal
        )

    def load(self, path: Optional[str] = None) -> None:
        """Load a previously saved index and metadata.

        Parameters
        ----------
        path : str, optional
            Directory to load from (default: ``config.FAISS_DIR``).

        Raises
        ------
        FileNotFoundError
            If the expected files are not found.
        """
        load_dir = Path(path) if path else Path(FAISS_DIR)
        index_path = load_dir / "index.faiss"
        meta_path = load_dir / "metadata.json"

        if not index_path.is_file():
            raise FileNotFoundError(f"FAISS index not found at {index_path}")
        if not meta_path.is_file():
            raise FileNotFoundError(f"Metadata file not found at {meta_path}")

        self.index = faiss.read_index(str(index_path))

        with open(meta_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        logger.info(
            "FAISS index loaded from %s (%d vectors).", load_dir, self.index.ntotal
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset the index and metadata list."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents.clear()
        logger.info("FAISS index cleared.")

    def __len__(self) -> int:
        return self.index.ntotal
