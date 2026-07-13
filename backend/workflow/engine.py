"""
workflow/engine.py - Durable workflow engine for Kizlly.

Orchestrates the 6-step contract review pipeline with retry policies,
human-in-the-loop pausing, and JSON-backed state persistence.  Mirrors
Render Workflows semantics: each step failure retries *only* that step;
previous successful steps are never re-executed.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config import WORKFLOW_DB_PATH
from models import (
    ClauseReviewDecision,
    StepStatus,
    WorkflowState,
    WorkflowStatus,
)
from workflow.audit_log import AuditLog

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Persistence directory
# ------------------------------------------------------------------ #
_WORKFLOW_DIR = Path(WORKFLOW_DB_PATH).parent / "workflow_states"
_WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ #
# Step definitions (retry policies)
# ------------------------------------------------------------------ #

STEP_DEFINITIONS: List[Dict[str, Any]] = [
    {"name": "ingest",           "max_retries": 3, "timeout": 60},
    {"name": "embed_and_search", "max_retries": 2, "timeout": 120},
    {"name": "risk_analysis",    "max_retries": 5, "timeout": 300},
    {"name": "human_approval",   "max_retries": 0, "timeout": None},  # Pauses indefinitely
    {"name": "graph_write",      "max_retries": 3, "timeout": 60},
    {"name": "audit_finalize",   "max_retries": 1, "timeout": 30},
]

STEP_NAMES: List[str] = [s["name"] for s in STEP_DEFINITIONS]


class WorkflowEngine:
    """Durable workflow engine with retry + human-in-the-loop support.

    Usage::

        audit = AuditLog()
        engine = WorkflowEngine(audit)
        wf = engine.start_workflow("contract-123", "/tmp/file.pdf", "file.pdf")
        # ... later, after human review ...
        wf = engine.resume_workflow("contract-123", decisions, reviewer)
    """

    def __init__(self, audit_log: AuditLog) -> None:
        """Initialise the engine.

        Args:
            audit_log: An :class:`AuditLog` instance for recording every
                       state transition.
        """
        self.audit_log = audit_log
        self._workflows: Dict[str, WorkflowState] = {}

        # Hydrate in-memory cache from persisted JSON files
        self._load_all_states()

    # ================================================================== #
    # Public API
    # ================================================================== #

    def start_workflow(
        self,
        contract_id: str,
        file_path: str,
        filename: str,
        vendor_name: Optional[str] = None,
        contract_title: Optional[str] = None,
        renewal_date: Optional[str] = None,
        embedder: Any = None,
        faiss_store: Any = None,
        risk_analyzer: Any = None,
        neo4j_client: Any = None,
    ) -> WorkflowState:
        """Start a new contract review workflow.

        Creates the initial :class:`WorkflowState`, runs the automated
        steps (ingest → embed → risk analysis), and pauses at the
        human-approval gate.

        Args:
            contract_id: Unique identifier for the contract.
            file_path:   Absolute path to the uploaded file on disk.
            filename:    Original filename (used to detect file type).
            vendor_name: Optional vendor name override.
            contract_title: Optional contract title override.
            renewal_date: Optional renewal date override.
            embedder: Embedder service.
            faiss_store: Vector store service.
            risk_analyzer: AI analysis service.
            neo4j_client: Neo4j graph client.

        Returns:
            The current :class:`WorkflowState` — may be
            ``PAUSED_FOR_REVIEW``, ``FAILED``, or ``COMPLETED``.
        """
        workflow = WorkflowState(
            contract_id=contract_id,
            status=WorkflowStatus.RUNNING,
            current_step=0,
            steps={name: StepStatus.QUEUED for name in STEP_NAMES},
        )

        self._workflows[contract_id] = workflow
        self._save_state(workflow)

        self.audit_log.log_event(
            workflow_id=contract_id,
            step="workflow",
            action="started",
            details=f"File: {filename}",
        )

        # ---- Run automated steps (0-3) ----
        # Step 0: ingest
        from workflow.steps import step_ingest

        workflow = self._execute_step(
            workflow, "ingest", step_ingest, workflow, file_path, vendor_name, contract_title, renewal_date
        )
        if workflow.status == WorkflowStatus.FAILED:
            return workflow

        # Step 1: embed_and_search
        from workflow.steps import step_embed_and_search

        workflow = self._execute_step(
            workflow, "embed_and_search", step_embed_and_search, workflow, embedder, faiss_store
        )
        if workflow.status == WorkflowStatus.FAILED:
            return workflow

        # Step 2: risk_analysis
        from workflow.steps import step_risk_analysis

        workflow = self._execute_step(
            workflow, "risk_analysis", step_risk_analysis, workflow, risk_analyzer
        )
        if workflow.status == WorkflowStatus.FAILED:
            return workflow

        # Step 3: human_approval — this *pauses* the workflow
        from workflow.steps import step_human_approval

        workflow = self._execute_step(
            workflow, "human_approval", step_human_approval, workflow
        )
        # After human_approval the status is PAUSED_FOR_REVIEW
        return workflow

    def list_workflows(self) -> List[WorkflowState]:
        """Return a list of all loaded workflow states."""
        return list(self._workflows.values())
    def get_workflow(self, contract_id: str) -> Optional[WorkflowState]:
        """Retrieve the current state of a workflow.

        Args:
            contract_id: The contract / workflow identifier.

        Returns:
            The :class:`WorkflowState`, or ``None`` if not found.
        """
        if contract_id in self._workflows:
            return self._workflows[contract_id]

        # Try loading from disk
        loaded = self._load_state(contract_id)
        if loaded:
            self._workflows[contract_id] = loaded
        return loaded

    def resume_workflow(
        self,
        contract_id: str,
        review_decisions: List[ClauseReviewDecision],
        reviewer: Dict[str, str],
        vendor_name: Optional[str] = None,
        contract_title: Optional[str] = None,
        renewal_date: Optional[str] = None,
        neo4j_client: Any = None,
    ) -> WorkflowState:
        """Resume a workflow after human approval.

        Picks up exactly where the pipeline left off: records the review
        decisions, then continues through *graph_write* and
        *audit_finalize*.

        Args:
            contract_id:      Identifier of the paused workflow.
            review_decisions: The reviewer's decisions on flagged clauses.
            reviewer:         Dict with ``id`` and ``name`` keys.
            vendor_name:      Optional vendor name override.
            contract_title:   Optional contract title override.
            renewal_date:     Optional renewal date override.
            neo4j_client:     Neo4j graph client.

        Returns:
            The final :class:`WorkflowState` (should be ``COMPLETED``
            or ``FAILED``).

        Raises:
            ValueError: If the workflow is not in ``PAUSED_FOR_REVIEW``.
        """
        workflow = self.get_workflow(contract_id)
        if workflow is None:
            raise ValueError(f"Workflow {contract_id} not found.")

        if workflow.status != WorkflowStatus.PAUSED_FOR_REVIEW:
            raise ValueError(
                f"Workflow {contract_id} is not paused for review "
                f"(current status: {workflow.status.value})."
            )

        # Record decisions
        workflow.review_decisions = review_decisions
        workflow.status = WorkflowStatus.RUNNING
        workflow.steps["human_approval"] = StepStatus.SUCCEEDED
        workflow.current_step = STEP_NAMES.index("graph_write")
        workflow.updated_at = datetime.now(timezone.utc)
        if workflow.contract_meta:
            if vendor_name:
                workflow.contract_meta.vendor_name = vendor_name
            if contract_title:
                workflow.contract_meta.title = contract_title
            if renewal_date:
                workflow.contract_meta.renewal_date = renewal_date
        self._save_state(workflow)

        self.audit_log.log_event(
            workflow_id=contract_id,
            step="human_approval",
            action="review_submitted",
            details=f"{len(review_decisions)} decisions by {reviewer.get('display_name', reviewer.get('username', 'unknown'))}",
            reviewer_id=reviewer.get("username"),
            reviewer_name=reviewer.get("display_name", reviewer.get("username")),
        )

        # Step 4: graph_write
        from workflow.steps import step_graph_write

        workflow = self._execute_step(
            workflow, "graph_write", step_graph_write, workflow, neo4j_client
        )
        if workflow.status == WorkflowStatus.FAILED:
            return workflow

        # Step 5: audit_finalize
        from workflow.steps import step_audit_finalize

        workflow = self._execute_step(
            workflow, "audit_finalize", step_audit_finalize, workflow, self.audit_log
        )
        return workflow

    # ================================================================== #
    # Step execution with retries
    # ================================================================== #

    def _execute_step(
        self,
        workflow: WorkflowState,
        step_name: str,
        step_func: Callable[..., WorkflowState],
        *args: Any,
    ) -> WorkflowState:
        """Execute a single pipeline step with retry logic.

        - On success the step is marked ``SUCCEEDED`` and the workflow
          advances.
        - On failure the step is retried up to ``max_retries`` times.
        - If all retries are exhausted the workflow is marked ``FAILED``.

        Args:
            workflow:  Current workflow state.
            step_name: Name matching a key in :data:`STEP_DEFINITIONS`.
            step_func: The callable that performs the actual work.
            *args:     Positional arguments forwarded to *step_func*.

        Returns:
            The (possibly updated) :class:`WorkflowState`.
        """
        step_def = next(
            (s for s in STEP_DEFINITIONS if s["name"] == step_name), None
        )
        if step_def is None:
            logger.error("Unknown step: %s", step_name)
            workflow.status = WorkflowStatus.FAILED
            workflow.error = f"Unknown step: {step_name}"
            self._save_state(workflow)
            return workflow

        max_retries: int = step_def["max_retries"]
        step_idx = STEP_NAMES.index(step_name)
        workflow.current_step = step_idx
        workflow.steps[step_name] = StepStatus.RUNNING
        workflow.updated_at = datetime.now(timezone.utc)
        self._save_state(workflow)

        self.audit_log.log_event(
            workflow_id=workflow.contract_id,
            step=step_name,
            action="step_started",
        )

        attempt = 0
        last_error: Optional[str] = None

        while attempt <= max_retries:
            try:
                workflow = step_func(*args)

                # human_approval step sets PAUSED_FOR_REVIEW
                if workflow.status == WorkflowStatus.PAUSED_FOR_REVIEW:
                    workflow.steps[step_name] = StepStatus.AWAITING_APPROVAL
                    self._save_state(workflow)
                    self.audit_log.log_event(
                        workflow_id=workflow.contract_id,
                        step=step_name,
                        action="awaiting_approval",
                    )
                    return workflow

                # Normal success
                workflow.steps[step_name] = StepStatus.SUCCEEDED
                workflow.current_step = step_idx + 1
                workflow.updated_at = datetime.now(timezone.utc)
                self._save_state(workflow)

                self.audit_log.log_event(
                    workflow_id=workflow.contract_id,
                    step=step_name,
                    action="step_succeeded",
                )
                return workflow

            except Exception as exc:
                attempt += 1
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Step %s attempt %d/%d failed: %s",
                    step_name,
                    attempt,
                    max_retries + 1,
                    last_error,
                )
                self.audit_log.log_event(
                    workflow_id=workflow.contract_id,
                    step=step_name,
                    action="step_retry" if attempt <= max_retries else "step_failed",
                    details=last_error,
                )

                if attempt <= max_retries:
                    workflow.steps[step_name] = StepStatus.RETRYING
                    self._save_state(workflow)
                    # Brief back-off (exponential, capped at 5 s)
                    time.sleep(min(2 ** attempt, 5))

        # Exhausted all retries
        workflow.status = WorkflowStatus.FAILED
        workflow.steps[step_name] = StepStatus.FAILED
        workflow.error = f"Step '{step_name}' failed after {max_retries + 1} attempts: {last_error}"
        workflow.updated_at = datetime.now(timezone.utc)
        self._save_state(workflow)

        self.audit_log.log_event(
            workflow_id=workflow.contract_id,
            step=step_name,
            action="workflow_failed",
            details=workflow.error,
        )
        return workflow

    # ================================================================== #
    # Persistence (JSON files)
    # ================================================================== #

    def _save_state(self, workflow: WorkflowState) -> None:
        """Persist a workflow state to a JSON file.

        Args:
            workflow: The state to persist.
        """
        try:
            path = _WORKFLOW_DIR / f"{workflow.contract_id}.json"
            path.write_text(workflow.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to save workflow state: %s", exc)

    def _load_state(self, contract_id: str) -> Optional[WorkflowState]:
        """Load a single workflow state from its JSON file.

        Args:
            contract_id: The identifier to look up.

        Returns:
            A :class:`WorkflowState`, or ``None`` if the file does not
            exist or is corrupt.
        """
        path = _WORKFLOW_DIR / f"{contract_id}.json"
        if not path.exists():
            return None
        try:
            data = path.read_text(encoding="utf-8")
            return WorkflowState.model_validate_json(data)
        except Exception as exc:
            logger.error("Failed to load workflow state for %s: %s", contract_id, exc)
            return None

    def _load_all_states(self) -> None:
        """Hydrate the in-memory cache from all persisted JSON files."""
        try:
            for path in _WORKFLOW_DIR.glob("*.json"):
                contract_id = path.stem
                state = self._load_state(contract_id)
                if state:
                    self._workflows[contract_id] = state
            logger.info(
                "Loaded %d persisted workflow(s) from disk.", len(self._workflows)
            )
        except Exception as exc:
            logger.error("Failed to load workflow states: %s", exc)
