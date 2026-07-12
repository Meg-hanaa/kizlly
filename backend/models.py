"""
models.py - Pydantic models for Kizlly API.

Defines data shapes for contracts, clauses, risk flags, vendors,
review decisions, audit entries, and workflow states.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskSeverity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RiskCategory(str, Enum):
    LIABILITY = "Liability"
    TERMINATION = "Termination"
    INDEMNIFICATION = "Indemnification"
    IP = "Intellectual Property"
    CONFIDENTIALITY = "Confidentiality"
    PAYMENT = "Payment"
    RENEWAL = "Renewal"
    GOVERNING_LAW = "Governing Law"
    DATA_PRIVACY = "Data Privacy"
    FORCE_MAJEURE = "Force Majeure"
    NON_COMPETE = "Non-Compete"
    OTHER = "Other"


class ReviewDecisionType(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED_FOR_REVIEW = "paused_for_review"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    AWAITING_APPROVAL = "awaiting_approval"


# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    display_name: str


# ---------------------------------------------------------------------------
# Clause & Risk Models
# ---------------------------------------------------------------------------

class ClauseChunk(BaseModel):
    """A chunk of text from a contract with metadata."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str
    page: Optional[int] = None
    section: Optional[str] = None
    char_offset: Optional[int] = None
    char_count: int = 0


class RiskFlag(BaseModel):
    """A risk flag on a specific clause."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    clause_id: str
    clause_text: str
    risk_type: str
    category: str = "Other"
    severity: RiskSeverity = RiskSeverity.MEDIUM
    explanation: str = ""
    ai_confidence: float = 0.0
    hinglish_explanation: Optional[str] = None


class ContradictionFlag(BaseModel):
    """A contradiction between two clauses."""
    clause_a_id: str
    clause_a_text: str
    clause_b_id: str
    clause_b_text: str
    explanation: str
    severity: RiskSeverity = RiskSeverity.HIGH


# ---------------------------------------------------------------------------
# Review Models
# ---------------------------------------------------------------------------

class ClauseReviewDecision(BaseModel):
    """A reviewer's decision on a single flagged clause."""
    clause_id: str
    decision: ReviewDecisionType
    comment: Optional[str] = ""


class ReviewSubmission(BaseModel):
    """A batch review submission from a reviewer."""
    decisions: List[ClauseReviewDecision]
    vendor_name: Optional[str] = None
    contract_title: Optional[str] = None
    renewal_date: Optional[str] = None  # ISO format: YYYY-MM-DD


# ---------------------------------------------------------------------------
# Contract Models
# ---------------------------------------------------------------------------

class ContractMetadata(BaseModel):
    """Metadata extracted from or assigned to a contract."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    filename: str
    title: Optional[str] = None
    vendor_name: Optional[str] = None
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    status: WorkflowStatus = WorkflowStatus.PENDING
    total_pages: int = 0
    total_chunks: int = 0
    total_chars: int = 0
    language: str = "English"
<<<<<<< HEAD
=======
    renewal_date: Optional[str] = None
    notice_deadline: Optional[str] = None
    auto_renewal: Optional[bool] = None
>>>>>>> 72c1ebc (Implement contract renewal alerts, fix graph visualization, layouts, and backend query routing)


class ContractUploadResponse(BaseModel):
    """Response after uploading a contract."""
    contract_id: str
    filename: str
    status: WorkflowStatus
    message: str


class ContractStatusResponse(BaseModel):
    """Current workflow status for a contract."""
    contract_id: str
    status: WorkflowStatus
    current_step: str
    steps: List[StepInfo]
    flagged_clauses: int = 0
    reviewed_clauses: int = 0


class StepInfo(BaseModel):
    """Information about a single workflow step."""
    name: str
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Dashboard / Portfolio Models
# ---------------------------------------------------------------------------

class VendorExposure(BaseModel):
    vendor: str
    industry: Optional[str] = None
    contract_count: int
    total_exposure: float = 0.0
    risk_flags: int = 0


class RenewalRisk(BaseModel):
    contract_id: str
    title: str
    vendor: str
    renewal_date: str
    value: float = 0.0
    urgency: str  # URGENT, SOON, UPCOMING


class ClausePattern(BaseModel):
    risk_type: str
    category: str
    vendor_count: int
    contract_count: int
    clause_count: int
    affected_vendors: List[str]


class PortfolioDashboard(BaseModel):
    total_contracts: int = 0
    active_vendors: int = 0
    flagged_clauses: int = 0
    approved_clauses: int = 0
    rejected_clauses: int = 0
    risk_distribution: Dict[str, int] = {}
    recent_uploads: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Graph Visualization Models
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # Contract, Vendor, Clause, RiskType
    properties: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # WITH_VENDOR, HAS_CLAUSE, FLAGGED_AS, etc.
    properties: Dict[str, Any] = {}


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ---------------------------------------------------------------------------
# Audit Models
# ---------------------------------------------------------------------------

class AuditEntry(BaseModel):
    id: Optional[int] = None
    workflow_id: str
    step: str
    action: str
    details: str = ""
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_sent_externally: Optional[str] = None  # Privacy: what was sent to Groq


class PrivacyLog(BaseModel):
    """Record of data sent to external APIs."""
    workflow_id: str
    timestamp: datetime
    api: str  # "groq"
    chars_sent: int
    chunk_count: int
    chunks_preview: List[str]  # First 50 chars of each chunk


# ---------------------------------------------------------------------------
# Workflow State (persisted)
# ---------------------------------------------------------------------------

class WorkflowState(BaseModel):
    """Complete state of a contract review workflow."""
    contract_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: int = 0
    steps: Dict[str, StepStatus] = {}
    contract_meta: Optional[ContractMetadata] = None
    extracted_text: Optional[str] = None
    chunks: List[ClauseChunk] = []
    risk_flags: List[RiskFlag] = []
    contradictions: List[ContradictionFlag] = []
    review_decisions: List[ClauseReviewDecision] = []
    privacy_logs: List[PrivacyLog] = []
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
