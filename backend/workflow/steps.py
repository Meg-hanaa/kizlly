"""
workflow/steps.py - The 6 workflow step functions for Kizlly.

Each function receives a :class:`WorkflowState` (plus any required
service objects), performs its work, mutates the state, and returns it.
Functions are designed to be called by :class:`WorkflowEngine` with
retry logic wrapped around them.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from models import (
    ClauseChunk,
    ContractMetadata,
    PrivacyLog,
    ReviewDecisionType,
    RiskFlag,
    StepStatus,
    WorkflowState,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


# ================================================================== #
# Step 1 — Ingest
# ================================================================== #

def step_ingest(
    workflow: WorkflowState,
    file_path: str,
) -> WorkflowState:
    """Parse an uploaded contract and extract raw text.

    Chooses the parser based on file extension (``.pdf`` or ``.docx``).

    Args:
        workflow:  Current workflow state.
        file_path: Absolute path to the uploaded file.

    Returns:
        Updated :class:`WorkflowState` with ``extracted_text`` and
        ``contract_meta`` populated.

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        ValueError:        If the file extension is unsupported.
    """
    logger.info("[ingest] Processing file: %s", file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        from ingestion.pdf_parser import parse_pdf
        text = parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        from ingestion.docx_parser import parse_docx
        text = parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Build contract metadata
    filename = os.path.basename(file_path)
    workflow.extracted_text = text
    workflow.contract_meta = ContractMetadata(
        id=workflow.contract_id,
        filename=filename,
        title=filename.rsplit(".", 1)[0],
        total_chars=len(text),
    )
    workflow.updated_at = datetime.now(timezone.utc)

    logger.info("[ingest] Extracted %d chars from %s", len(text), filename)
    return workflow


# ================================================================== #
# Step 2 — Embed & Search
# ================================================================== #

def step_embed_and_search(
    workflow: WorkflowState,
    embedder: Any = None,
    faiss_store: Any = None,
) -> WorkflowState:
    """Chunk text, generate embeddings, and build / update a FAISS index.

    If *embedder* or *faiss_store* are ``None`` the step still performs
    chunking so downstream steps have ``workflow.chunks`` available.

    Args:
        workflow:    Current workflow state (must have ``extracted_text``).
        embedder:    Embedding service (optional).
        faiss_store: FAISS index wrapper (optional).

    Returns:
        Updated :class:`WorkflowState` with ``chunks`` populated.
    """
    logger.info("[embed_and_search] Chunking text for %s", workflow.contract_id)

    if not workflow.extracted_text:
        raise ValueError("No extracted text to chunk. Run ingest first.")

    from ingestion.chunker import chunk_text

    raw_chunks = chunk_text(workflow.extracted_text)

    clause_chunks = []
    for idx, chunk in enumerate(raw_chunks):
        text = chunk if isinstance(chunk, str) else chunk.get("text", str(chunk))
        section = chunk.get("section") if isinstance(chunk, dict) else None
        clause_chunks.append(
            ClauseChunk(
                text=text,
                section=section,
                char_offset=idx,
                char_count=len(text),
            )
        )

    workflow.chunks = clause_chunks

    if workflow.contract_meta:
        workflow.contract_meta.total_chunks = len(clause_chunks)

    # Generate embeddings if services are available
    if embedder is not None and faiss_store is not None:
        try:
            texts = [c.text for c in clause_chunks]
            vectors = embedder.encode(texts)
            faiss_store.add(
                vectors,
                [{"id": c.id, "text": c.text} for c in clause_chunks],
            )
            logger.info(
                "[embed_and_search] Added %d vectors to FAISS", len(vectors)
            )
        except Exception as exc:
            logger.warning("[embed_and_search] Embedding failed (non-fatal): %s", exc)

    workflow.updated_at = datetime.now(timezone.utc)
    logger.info(
        "[embed_and_search] Created %d chunks for %s",
        len(clause_chunks),
        workflow.contract_id,
    )
    return workflow


# ================================================================== #
# Step 3 — Risk analysis
# ================================================================== #

def step_risk_analysis(
    workflow: WorkflowState,
    risk_analyzer: Any = None,
) -> WorkflowState:
    """Analyse each chunk for risk using the Groq LLaMA risk analyser.

    Privacy guard: only short (2-3 sentence) chunks are sent externally.
    The step records every outbound payload in ``workflow.privacy_logs``.

    If *risk_analyzer* is ``None`` the step is a no-op (no LLM call) so
    the pipeline can still be tested end-to-end without a Groq key.

    Args:
        workflow:      Current workflow state (must have ``chunks``).
        risk_analyzer: AI risk analyser service (optional).

    Returns:
        Updated :class:`WorkflowState` with ``risk_flags``,
        ``contradictions``, and ``privacy_logs``.
    """
    logger.info("[risk_analysis] Analysing %d chunks", len(workflow.chunks))

    if not workflow.chunks:
        logger.warning("[risk_analysis] No chunks to analyse.")
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    if risk_analyzer is None:
        logger.warning(
            "[risk_analysis] No risk_analyzer provided — skipping AI analysis."
        )
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    risk_flags: list[RiskFlag] = []
    chunks_sent: list[str] = []
    total_chars_sent = 0

    for chunk in workflow.chunks:
        # Privacy: limit to 2-3 sentence chunks
        sentences = chunk.text.split(".")
        truncated = ".".join(sentences[:3]).strip()
        if truncated and not truncated.endswith("."):
            truncated += "."

        try:
            analysis = risk_analyzer.analyze(truncated)

            if analysis and isinstance(analysis, dict):
                flags = analysis.get("flags", [])
                for flag_data in flags:
                    risk_flags.append(
                        RiskFlag(
                            clause_id=chunk.id,
                            clause_text=chunk.text,
                            risk_type=flag_data.get("risk_type", "Unknown"),
                            category=flag_data.get("category", "Other"),
                            severity=flag_data.get("severity", "Medium"),
                            explanation=flag_data.get("explanation", ""),
                            ai_confidence=flag_data.get("confidence", 0.0),
                        )
                    )

                # Record contradictions
                contradictions = analysis.get("contradictions", [])
                workflow.contradictions.extend(contradictions)

            chunks_sent.append(truncated[:50])
            total_chars_sent += len(truncated)

        except Exception as exc:
            logger.warning(
                "[risk_analysis] Chunk %s failed: %s", chunk.id, exc
            )

    workflow.risk_flags = risk_flags

    # Privacy log: what was sent to Groq
    if chunks_sent:
        workflow.privacy_logs.append(
            PrivacyLog(
                workflow_id=workflow.contract_id,
                timestamp=datetime.now(timezone.utc),
                api="groq",
                chars_sent=total_chars_sent,
                chunk_count=len(chunks_sent),
                chunks_preview=chunks_sent,
            )
        )

    workflow.updated_at = datetime.now(timezone.utc)
    logger.info(
        "[risk_analysis] Found %d risk flags for %s",
        len(risk_flags),
        workflow.contract_id,
    )
    return workflow


# ================================================================== #
# Step 4 — Human approval
# ================================================================== #

def step_human_approval(workflow: WorkflowState) -> WorkflowState:
    """Pause the workflow for human review.

    Sets the workflow status to ``PAUSED_FOR_REVIEW``. The engine
    detects this and halts execution until :meth:`resume_workflow` is
    called.

    Args:
        workflow: Current workflow state.

    Returns:
        Updated :class:`WorkflowState` with ``PAUSED_FOR_REVIEW`` status.
    """
    logger.info(
        "[human_approval] Pausing workflow %s for review (%d risk flags)",
        workflow.contract_id,
        len(workflow.risk_flags),
    )

    workflow.status = WorkflowStatus.PAUSED_FOR_REVIEW
    workflow.steps["human_approval"] = StepStatus.AWAITING_APPROVAL
    workflow.updated_at = datetime.now(timezone.utc)

    return workflow


# ================================================================== #
# Step 5 — Graph write
# ================================================================== #

def step_graph_write(
    workflow: WorkflowState,
    neo4j_client: Any = None,
) -> WorkflowState:
    """Write approved data to Neo4j AuraDB.

    Only clauses whose review decision is ``approved`` are written.
    If *neo4j_client* is ``None`` or not connected the step completes
    gracefully — data is simply not persisted to the graph.

    Args:
        workflow:     Current workflow state (must have ``review_decisions``).
        neo4j_client: An initialised :class:`Neo4jClient` (optional).

    Returns:
        Updated :class:`WorkflowState`.
    """
    logger.info("[graph_write] Writing to Neo4j for %s", workflow.contract_id)

    if neo4j_client is None:
        logger.warning("[graph_write] No Neo4j client — skipping graph write.")
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    # Check connection
    if hasattr(neo4j_client, "is_connected") and not neo4j_client.is_connected:
        logger.warning("[graph_write] Neo4j not connected — skipping.")
        workflow.updated_at = datetime.now(timezone.utc)
        return workflow

    # Build lookup of approved clause IDs
    approved_ids = {
        d.clause_id
        for d in workflow.review_decisions
        if d.decision == ReviewDecisionType.APPROVED
    }

    try:
        # Create contract & vendor node
        meta = workflow.contract_meta
        if meta:
            neo4j_client.create_contract(
                contract_id=meta.id,
                title=meta.title or meta.filename,
                vendor_name=meta.vendor_name or "Unknown Vendor",
                effective_date=None,
                expiration_date=None,
                value=0.0,
                status=meta.status.value if meta.status else "Active",
            )

        # Create clause + risk nodes for approved clauses only
        for risk_flag in workflow.risk_flags:
            if risk_flag.clause_id not in approved_ids:
                continue

            # Find matching chunk for the full text
            chunk_text = risk_flag.clause_text
            section = None
            for chunk in workflow.chunks:
                if chunk.id == risk_flag.clause_id:
                    section = chunk.section
                    break

            neo4j_client.create_clause(
                clause_id=risk_flag.clause_id,
                contract_id=workflow.contract_id,
                clause_type=risk_flag.category,
                text=chunk_text,
                section=section,
                severity=risk_flag.severity.value if hasattr(risk_flag.severity, "value") else str(risk_flag.severity),
            )

            neo4j_client.flag_clause_risk(
                clause_id=risk_flag.clause_id,
                risk_type_name=risk_flag.risk_type,
                category=risk_flag.category,
                confidence=risk_flag.ai_confidence,
            )

        logger.info(
            "[graph_write] Wrote %d approved clauses to Neo4j",
            len(approved_ids),
        )
    except Exception as exc:
        logger.error("[graph_write] Neo4j write error (non-fatal): %s", exc)

    workflow.updated_at = datetime.now(timezone.utc)
    return workflow


# ================================================================== #
# Step 6 — Audit finalise
# ================================================================== #

def step_audit_finalize(
    workflow: WorkflowState,
    audit_log: Any = None,
) -> WorkflowState:
    """Finalise the audit trail and mark the workflow as COMPLETED.

    Writes a summary entry covering the entire pipeline run, including
    counts of chunks, risk flags, and review decisions.

    Args:
        workflow:  Current workflow state.
        audit_log: An :class:`AuditLog` instance (optional).

    Returns:
        Updated :class:`WorkflowState` with ``COMPLETED`` status.
    """
    logger.info("[audit_finalize] Finalising workflow %s", workflow.contract_id)

    approved = sum(
        1 for d in workflow.review_decisions
        if d.decision == ReviewDecisionType.APPROVED
    )
    rejected = sum(
        1 for d in workflow.review_decisions
        if d.decision == ReviewDecisionType.REJECTED
    )
    flagged = sum(
        1 for d in workflow.review_decisions
        if d.decision == ReviewDecisionType.FLAGGED
    )

    summary = (
        f"Workflow completed | "
        f"Chunks: {len(workflow.chunks)} | "
        f"Risk flags: {len(workflow.risk_flags)} | "
        f"Contradictions: {len(workflow.contradictions)} | "
        f"Decisions — approved: {approved}, rejected: {rejected}, flagged: {flagged}"
    )

    if audit_log is not None:
        try:
            audit_log.log_event(
                workflow_id=workflow.contract_id,
                step="audit_finalize",
                action="workflow_completed",
                details=summary,
            )

            # Log privacy summary
            if workflow.privacy_logs:
                total_chars = sum(p.chars_sent for p in workflow.privacy_logs)
                total_chunks = sum(p.chunk_count for p in workflow.privacy_logs)
                audit_log.log_event(
                    workflow_id=workflow.contract_id,
                    step="audit_finalize",
                    action="privacy_summary",
                    details=f"Total chars sent to Groq: {total_chars}, chunks: {total_chunks}",
                    data_sent_externally=f"groq: {total_chars} chars across {total_chunks} chunks",
                )
        except Exception as exc:
            logger.error("[audit_finalize] Audit write error: %s", exc)

    workflow.status = WorkflowStatus.COMPLETED
    workflow.steps["audit_finalize"] = StepStatus.SUCCEEDED
    workflow.updated_at = datetime.now(timezone.utc)

    logger.info("[audit_finalize] %s", summary)
    return workflow
