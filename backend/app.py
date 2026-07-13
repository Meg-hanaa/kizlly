"""
app.py - Main FastAPI application for Kizlly.

Provides REST endpoints for:
- Authentication (login/register)
- Contract upload and workflow management
- Clause review (human approval checkpoint)
- Portfolio dashboard (graph-powered queries)
- Audit trail
- Privacy transparency
"""

import os
import uuid
import shutil
import asyncio
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from config import (
    APP_NAME, APP_VERSION, APP_DESCRIPTION, UPLOAD_DIR, PORT,
    NEO4J_URI, DEBUG
)
from models import (
    UserRegister, UserLogin, TokenResponse,
    ContractUploadResponse, ContractStatusResponse, StepInfo,
    ReviewSubmission, PortfolioDashboard, GraphData,
    WorkflowStatus, StepStatus, ReviewDecisionType,
)
from auth import (
    register_user, authenticate_user, create_token,
    get_current_user, get_optional_user,
)

# ---------------------------------------------------------------------------
# Lazy-loaded service singletons (avoid import errors if deps missing)
# ---------------------------------------------------------------------------
_embedder = None
_faiss_store = None
_groq_client = None
_risk_analyzer = None
_hinglish_explainer = None
_neo4j_client = None
_audit_log = None
_workflow_engine = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from embeddings.embedder import Embedder
        _embedder = Embedder()
    return _embedder


def get_faiss_store():
    global _faiss_store
    if _faiss_store is None:
        from vectorstore.faiss_store import FAISSStore
        _faiss_store = FAISSStore()
    return _faiss_store


def get_groq_client():
    global _groq_client
    if _groq_client is None:
        from llm.groq_client import GroqClient
        _groq_client = GroqClient()
    return _groq_client


def get_risk_analyzer():
    global _risk_analyzer
    if _risk_analyzer is None:
        from llm.risk_analyzer import RiskAnalyzer
        _risk_analyzer = RiskAnalyzer()
    return _risk_analyzer


def get_hinglish_explainer():
    global _hinglish_explainer
    if _hinglish_explainer is None:
        from llm.hinglish_explainer import HinglishExplainer
        _hinglish_explainer = HinglishExplainer()
    return _hinglish_explainer


def get_neo4j_client():
    global _neo4j_client
    if _neo4j_client is None:
        if not NEO4J_URI:
            return None
        try:
            from graph.neo4j_client import Neo4jClient
            _neo4j_client = Neo4jClient()
        except Exception as e:
            print(f"[WARN] Neo4j connection failed: {e}")
            return None
    return _neo4j_client


def get_audit_log():
    global _audit_log
    if _audit_log is None:
        from workflow.audit_log import AuditLog
        _audit_log = AuditLog()
    return _audit_log


def get_workflow_engine():
    global _workflow_engine
    if _workflow_engine is None:
        from workflow.engine import WorkflowEngine
        _workflow_engine = WorkflowEngine(get_audit_log())
    return _workflow_engine


# ---------------------------------------------------------------------------
# Renewal watch background worker and date helpers
# ---------------------------------------------------------------------------

def parse_date(date_str: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def get_time_remaining_label(diff_seconds: float) -> str:
    if diff_seconds < 0:
        return "Expired"
    if diff_seconds < 60:
        return f"{int(diff_seconds)}s remaining"
    if diff_seconds < 3600:
        return f"{int(diff_seconds // 60)}m remaining"
    if diff_seconds < 86400:
        return f"{int(diff_seconds // 3600)}h remaining"
    return f"{int(diff_seconds // 86400)}d remaining"


def calculate_trigger_dates(renewal_dt: datetime) -> dict[str, datetime]:
    now = datetime.now(timezone.utc)
    diff = renewal_dt - now
    # Scale triggers for demo context if date is set to near-future
    if diff.total_seconds() < 86400:
        return {
            "90_day": renewal_dt - timedelta(seconds=90),
            "60_day": renewal_dt - timedelta(seconds=60),
            "30_day": renewal_dt - timedelta(seconds=30)
        }
    else:
        return {
            "90_day": renewal_dt - timedelta(days=90),
            "60_day": renewal_dt - timedelta(days=60),
            "30_day": renewal_dt - timedelta(days=30)
        }


def get_contract_details(contract_id: str, neo4j_client=None) -> dict:
    from typing import Any
    if neo4j_client and neo4j_client.is_connected:
        try:
            query = """
            MATCH (c:Contract {id: $contract_id})
            MATCH (c)-[:WITH_VENDOR]->(v:Vendor)
            RETURN c.title AS title, v.name AS vendor_name, c.renewal_date AS renewal_date
            """
            res = neo4j_client.run_query(query, {"contract_id": contract_id})
            if res:
                return {
                    "title": res[0].get("title"),
                    "vendor_name": res[0].get("vendor_name"),
                    "renewal_date": res[0].get("renewal_date")
                }
        except Exception as e:
            print(f"[WARN] Failed to query contract details from Neo4j: {e}")

    try:
        import json
        from config import WORKFLOW_DB_PATH
        _WORKFLOW_DIR = Path(WORKFLOW_DB_PATH).parent / "workflow_states"
        path = _WORKFLOW_DIR / f"{contract_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("contract_meta", {})
            return {
                "title": meta.get("title") or meta.get("filename"),
                "vendor_name": meta.get("vendor_name") or "Unknown Vendor",
                "renewal_date": meta.get("renewal_date")
            }
    except Exception as e:
        print(f"[ERROR] Failed to load contract details from workflow JSON: {e}")

    return {
        "title": "Unknown Contract",
        "vendor_name": "Unknown Vendor",
        "renewal_date": None
    }


async def check_and_fire_alerts():
    import json
    from config import WORKFLOW_DB_PATH
    from workflow.alerts import alert_manager

    _WORKFLOW_DIR = Path(WORKFLOW_DB_PATH).parent / "workflow_states"
    if not _WORKFLOW_DIR.exists():
        return

    now = datetime.now(timezone.utc)
    neo4j = get_neo4j_client()

    for path in _WORKFLOW_DIR.glob("*.json"):
        try:
            contract_id = path.stem
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("contract_meta")
            if not meta:
                continue

            renewal_date_str = meta.get("renewal_date")
            if not renewal_date_str:
                continue

            renewal_dt = parse_date(renewal_date_str)
            if not renewal_dt:
                continue

            triggers = calculate_trigger_dates(renewal_dt)

            for alert_type, trigger_dt in triggers.items():
                if now >= trigger_dt:
                    if not alert_manager.has_alert_fired(contract_id, alert_type):
                        alert_id = str(uuid.uuid4())[:8]
                        fired_at_str = now.isoformat()

                        # SQLite store
                        alert_manager.create_alert(
                            alert_id=alert_id,
                            contract_id=contract_id,
                            alert_type=alert_type,
                            fired_at=fired_at_str,
                            status="unseen"
                        )

                        # Neo4j store
                        if neo4j and neo4j.is_connected:
                            try:
                                neo4j.create_alert(
                                    alert_id=alert_id,
                                    contract_id=contract_id,
                                    alert_type=alert_type,
                                    fired_at=fired_at_str,
                                    status="unseen"
                                )
                            except Exception as e:
                                print(f"[ERROR] Failed to write alert to Neo4j: {e}")

                        # SQLite Audit
                        audit = get_audit_log()
                        audit.log_event(
                            workflow_id=contract_id,
                            step="renewal_watch",
                            action="alert_fired",
                            details=f"Renewal alert of type {alert_type} fired. Status: unseen."
                        )

                        # Neo4j AuditEvent
                        if neo4j and neo4j.is_connected:
                            try:
                                neo4j.log_audit_event(
                                    contract_id=contract_id,
                                    action="alert_fired",
                                    details=f"Renewal alert of type {alert_type} fired."
                                )
                            except Exception as e:
                                print(f"[ERROR] Failed to write AuditEvent to Neo4j: {e}")
        except Exception as e:
            print(f"[ERROR] Error processing contract alert for path {path}: {e}")


async def run_renewal_watch_loop():
    print("[INFO] Starting renewal watch background loop...")
    while True:
        try:
            await check_and_fire_alerts()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[ERROR] Error in renewal watch background check: {e}")
        await asyncio.sleep(10)
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    print(f"[INFO] {APP_NAME} v{APP_VERSION} starting...")

    # Initialize Neo4j schema if connected
    neo4j = get_neo4j_client()
    if neo4j:
        try:
            from graph.schema import initialize_schema
            initialize_schema(neo4j)
            print("[INFO] Neo4j schema initialized")
        except Exception as e:
            print(f"[WARN] Neo4j schema init failed: {e}")

    # Start renewal watch loop task
    loop_task = asyncio.create_task(run_renewal_watch_loop())
    print(f"[INFO] {APP_NAME} ready on port {PORT}")

    yield

    # Shutdown
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    if _neo4j_client:
        _neo4j_client.close()
    print(f"[INFO] {APP_NAME} shutting down")


# ---------------------------------------------------------------------------
# Create FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=dict)
async def api_register(user: UserRegister):
    """Register a new reviewer account."""
    result = register_user(user.username, user.password, user.display_name)
    token = create_token(result["username"], result["display_name"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": result["username"],
        "display_name": result["display_name"],
    }


@app.post("/api/auth/login", response_model=dict)
async def api_login(user: UserLogin):
    """Authenticate a reviewer."""
    result = authenticate_user(user.username, user.password)
    token = create_token(result["username"], result["display_name"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": result["username"],
        "display_name": result["display_name"],
    }


# ---------------------------------------------------------------------------
# CONTRACT ENDPOINTS
# ---------------------------------------------------------------------------

@app.post("/api/contracts/upload", response_model=ContractUploadResponse)
async def api_upload_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    vendor_name: str = Form(default=""),
    contract_title: str = Form(default=""),
    renewal_date: str = Form(default=""),
    user: dict = Depends(get_current_user),
):
    """Upload a contract securely and start the review workflow."""
    # 1. Enforce strict extension verification
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    # Handle path traversal / sanitize input filename
    raw_filename = os.path.basename(file.filename)
    ext = os.path.splitext(raw_filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # 2. Enforce strict file size limits (e.g. 10MB)
    max_size_bytes = 10 * 1024 * 1024
    content_size = 0
    
    # 3. Generate random UUID filename and store outside public folder (UPLOAD_DIR is configured outside public)
    contract_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{contract_id}{ext}"
    
    # Verify path traversal protection
    if not str(file_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
         raise HTTPException(400, "Invalid file path target")

    try:
        with open(file_path, "wb") as f:
            while chunk := file.file.read(8192):
                content_size += len(chunk)
                if content_size > max_size_bytes:
                    raise HTTPException(413, "File exceeds maximum upload size of 10MB")
                f.write(chunk)
    except HTTPException:
        # Clean up partial file on limits failure
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(500, f"Failed to save upload: {str(e)}")

    # Log upload to audit
    audit = get_audit_log()
    audit.log_event(
        workflow_id=contract_id,
        step="upload",
        action="contract_uploaded",
        details=f"File: {raw_filename}, Vendor: {vendor_name}, Title: {contract_title}",
        reviewer_id=user["username"],
        reviewer_name=user["display_name"],
    )

    # Start workflow in background
    background_tasks.add_task(
        _run_workflow,
        contract_id=contract_id,
        file_path=str(file_path),
        filename=raw_filename,
        vendor_name=vendor_name,
        contract_title=contract_title,
        renewal_date=renewal_date,
        reviewer=user,
    )

    return ContractUploadResponse(
        contract_id=contract_id,
        filename=raw_filename,
        status=WorkflowStatus.PENDING,
        message="Contract uploaded. Workflow starting...",
    )


async def _run_workflow(
    contract_id: str,
    file_path: str,
    filename: str,
    vendor_name: str,
    contract_title: str,
    renewal_date: str,
    reviewer: dict,
):
    """Execute the contract review workflow (runs in background)."""
    try:
        engine = get_workflow_engine()
        engine.start_workflow(
            contract_id=contract_id,
            file_path=file_path,
            filename=filename,
            vendor_name=vendor_name,
            contract_title=contract_title,
            renewal_date=renewal_date,
            embedder=get_embedder(),
            faiss_store=get_faiss_store(),
            risk_analyzer=get_risk_analyzer(),
            neo4j_client=get_neo4j_client(),
            owner=reviewer.get("username") if reviewer else None,
        )
    except Exception as e:
        print(f"[ERROR] Workflow failed for {contract_id}: {e}")
        traceback.print_exc()
        audit = get_audit_log()
        audit.log_event(
            workflow_id=contract_id,
            step="workflow",
            action="workflow_error",
            details=str(e),
        )


@app.get("/api/contracts")
async def api_list_contracts(user: dict = Depends(get_current_user)):
    """List all contracts belonging to the current user."""
    engine = get_workflow_engine()
    username = user.get("username")
    workflows = engine.list_workflows(owner=username)
    return {"contracts": workflows}


@app.get("/api/contracts/{contract_id}/status")
async def api_contract_status(contract_id: str, user: dict = Depends(get_current_user)):
    """Get current workflow status for a contract."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(contract_id)
    if not workflow:
        raise HTTPException(404, "Contract not found")
    if workflow.owner != user.get("username"):
        raise HTTPException(403, "Access denied: you do not own this contract")
    return workflow


@app.delete("/api/contracts/{contract_id}")
async def api_delete_contract(contract_id: str, user: dict = Depends(get_current_user)):
    """Delete a contract and purge all workflow files."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(contract_id)
    if not workflow:
        raise HTTPException(404, "Contract not found")
    if workflow.owner != user.get("username"):
        raise HTTPException(403, "Access denied: you do not own this contract")
        
    deleted = engine.delete_workflow(contract_id)
    
    # Audit log the purge event
    audit = get_audit_log()
    audit.log_event(
        workflow_id=contract_id,
        step="purge",
        action="contract_deleted",
        details=f"Purged contract state and document templates",
        reviewer_id=user["username"],
        reviewer_name=user["display_name"],
    )
    
    return {"message": "Contract deleted successfully", "deleted": deleted}


@app.get("/api/contracts/{contract_id}/clauses")
async def api_contract_clauses(contract_id: str, user: dict = Depends(get_current_user)):
    """Get flagged clauses for a contract awaiting review."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(contract_id)
    if not workflow:
        raise HTTPException(404, "Contract not found")
    if workflow.owner != user.get("username"):
        raise HTTPException(403, "Access denied: you do not own this contract")
    return {
        "contract_id": contract_id,
        "status": workflow.status,
        "risk_flags": workflow.risk_flags,
        "contradictions": workflow.contradictions,
        "privacy_logs": workflow.privacy_logs,
    }


@app.post("/api/contracts/{contract_id}/review")
async def api_submit_review(
    contract_id: str,
    review: ReviewSubmission,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Submit review decisions for flagged clauses (human approval checkpoint)."""
    engine = get_workflow_engine()
    workflow = engine.get_workflow(contract_id)
    if not workflow:
        raise HTTPException(404, "Contract not found")
    if workflow.owner != user.get("username"):
        raise HTTPException(403, "Access denied: you do not own this contract")

    if workflow.status != WorkflowStatus.PAUSED_FOR_REVIEW:
        raise HTTPException(400, "Contract is not awaiting review")

    # Log each decision to audit
    audit = get_audit_log()
    for decision in review.decisions:
        audit.log_event(
            workflow_id=contract_id,
            step="human_approval",
            action=f"clause_{decision.decision}",
            details=f"Clause {decision.clause_id}: {decision.comment or 'No comment'}",
            reviewer_id=user["username"],
            reviewer_name=user["display_name"],
        )

    # Resume workflow in background
    background_tasks.add_task(
        _resume_workflow,
        contract_id=contract_id,
        review=review,
        reviewer=user,
    )

    return {"message": "Review submitted. Workflow resuming...", "status": "resuming"}


async def _resume_workflow(contract_id: str, review: ReviewSubmission, reviewer: dict):
    """Resume workflow after human approval."""
    try:
        engine = get_workflow_engine()
        engine.resume_workflow(
            contract_id=contract_id,
            review_decisions=review.decisions,
            vendor_name=review.vendor_name,
            contract_title=review.contract_title,
            renewal_date=review.renewal_date,
            reviewer=reviewer,
            neo4j_client=get_neo4j_client(),
        )
    except Exception as e:
        print(f"[ERROR] Resume failed for {contract_id}: {e}")
        traceback.print_exc()


# ---------------------------------------------------------------------------
# PORTFOLIO DASHBOARD ENDPOINTS (Graph-powered)
# ---------------------------------------------------------------------------

@app.get("/api/portfolio/dashboard")
async def api_portfolio_dashboard(user: dict = Depends(get_current_user)):
    """Get portfolio dashboard stats powered by Neo4j graph queries."""
    neo4j = get_neo4j_client()
    if not neo4j:
        # Return demo data if Neo4j not configured
        return _demo_dashboard(owner=user.get("username"))

    try:
        from graph.queries import get_portfolio_stats
        stats = get_portfolio_stats(neo4j, owner=user.get("username"))
        return stats
    except Exception as e:
        print(f"[WARN] Dashboard query failed: {e}")
        return _demo_dashboard(owner=user.get("username"))


@app.get("/api/portfolio/graph")
async def api_graph_data(user: dict = Depends(get_current_user)):
    """Get graph data for D3.js visualization."""
    neo4j = get_neo4j_client()
    if not neo4j:
        return {"nodes": [], "edges": []}

    try:
        data = neo4j.get_graph_data(owner=user.get("username"))
        return data
    except Exception as e:
        print(f"[WARN] Graph query failed: {e}")
        return {"nodes": [], "edges": []}


@app.get("/api/portfolio/vendor-exposure")
async def api_vendor_exposure(user: dict = Depends(get_current_user)):
    """Get cross-contract vendor exposure data."""
    neo4j = get_neo4j_client()
    if not neo4j:
        return {"vendors": []}

    try:
        from graph.queries import get_vendor_exposure
        return {"vendors": get_vendor_exposure(neo4j, owner=user.get("username"))}
    except Exception as e:
        print(f"[WARN] Vendor exposure query failed: {e}")
        return {"vendors": []}


@app.get("/api/portfolio/renewal-risk")
async def api_renewal_risk(
    days: int = 90,
    user: dict = Depends(get_current_user),
):
    """Get renewal cascade risk within a date window."""
    neo4j = get_neo4j_client()
    if not neo4j:
        return {"renewals": []}

    try:
        from graph.queries import get_renewal_risk
        return {"renewals": get_renewal_risk(neo4j, days, owner=user.get("username"))}
    except Exception as e:
        print(f"[WARN] Renewal risk query failed: {e}")
        return {"renewals": []}


@app.get("/api/portfolio/clause-patterns")
async def api_clause_patterns(user: dict = Depends(get_current_user)):
    """Get repeated risky clause patterns across vendors."""
    neo4j = get_neo4j_client()
    if not neo4j:
        return {"patterns": []}

    try:
        from graph.queries import get_clause_patterns
        return {"patterns": get_clause_patterns(neo4j)}
    except Exception as e:
        print(f"[WARN] Clause patterns query failed: {e}")
        return {"patterns": []}


# ---------------------------------------------------------------------------
# HINGLISH EXPLANATION
# ---------------------------------------------------------------------------

@app.post("/api/explain/hinglish")
async def api_hinglish(
    clause_text: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """Get a Hinglish explanation of a legal clause."""
    try:
        explainer = get_hinglish_explainer()
        explanation = explainer.explain(clause_text)
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(500, f"Hinglish explanation failed: {str(e)}")


# ---------------------------------------------------------------------------
# RENEWAL ALERTS
# ---------------------------------------------------------------------------

@app.get("/api/contracts/alerts")
async def api_get_alerts(user: dict = Depends(get_current_user)):
    """Retrieve all unseen renewal alerts."""
    from workflow.alerts import alert_manager
    alerts = alert_manager.get_unseen_alerts()
    result = []
    
    neo4j = get_neo4j_client()
    now = datetime.now(timezone.utc)
    
    for alert in alerts:
        # Verify contract ownership before delivering alert
        details = get_contract_details(alert["contract_id"], neo4j)
        
        # Load state details to check owner parameter
        engine = get_workflow_engine()
        workflow = engine.get_workflow(alert["contract_id"])
        if not workflow or workflow.owner != user.get("username"):
            continue

        renewal_date_str = details.get("renewal_date")
        days_remaining = None
        time_label = "N/A"
        
        if renewal_date_str:
            renewal_dt = parse_date(renewal_date_str)
            if renewal_dt:
                diff = renewal_dt - now
                diff_seconds = diff.total_seconds()
                time_label = get_time_remaining_label(diff_seconds)
                
                # Compute days_remaining for color indicators in frontend
                if diff_seconds < 86400:
                    if diff_seconds <= 30:
                        days_remaining = 15
                    elif diff_seconds <= 60:
                        days_remaining = 45
                    else:
                        days_remaining = 75
                else:
                    days_remaining = diff.days
                    
        result.append({
            "id": alert["id"],
            "contract_id": alert["contract_id"],
            "contract_title": details.get("title") or "Untitled Contract",
            "vendor_name": details.get("vendor_name") or "Unknown Vendor",
            "alert_type": alert["alert_type"],
            "fired_at": alert["fired_at"],
            "status": alert["status"],
            "days_remaining": days_remaining,
            "time_label": time_label
        })
        
    return {"alerts": result}


@app.post("/api/contracts/alerts/{alert_id}/seen")
async def api_mark_alert_seen(alert_id: str, user: dict = Depends(get_current_user)):
    """Mark a renewal alert as seen and log this to SQLite and Neo4j audit trails."""
    from workflow.alerts import alert_manager
    alert = alert_manager.get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
        
    engine = get_workflow_engine()
    workflow = engine.get_workflow(alert["contract_id"])
    if not workflow or workflow.owner != user.get("username"):
        raise HTTPException(403, "Access denied: you do not own this alert")
        
    # SQLite status update
    alert_manager.mark_alert_seen(alert_id)
    
    # Neo4j status update
    neo4j = get_neo4j_client()
    if neo4j and neo4j.is_connected:
        try:
            neo4j.mark_alert_seen_neo4j(alert_id)
        except Exception as e:
            print(f"[WARN] Failed to mark alert seen in Neo4j: {e}")
            
    # SQLite Audit Log
    audit = get_audit_log()
    audit.log_event(
        workflow_id=alert["contract_id"],
        step="renewal_watch",
        action="alert_seen",
        details=f"Alert of type {alert['alert_type']} marked as seen.",
        reviewer_id=user["username"],
        reviewer_name=user["display_name"]
    )
    
    # Neo4j AuditEvent
    if neo4j and neo4j.is_connected:
        try:
            neo4j.log_audit_event(
                contract_id=alert["contract_id"],
                action="alert_seen",
                details=f"Alert of type {alert['alert_type']} marked as seen.",
                reviewer_id=user["username"],
                reviewer_name=user["display_name"]
            )
        except Exception as e:
            print(f"[WARN] Failed to write AuditEvent to Neo4j: {e}")
            
    return {"message": "Alert marked as seen", "status": "seen"}


# ---------------------------------------------------------------------------
# AUDIT TRAIL
# ---------------------------------------------------------------------------

@app.get("/api/audit/log")
async def api_audit_log(
    workflow_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get the immutable audit trail scoped to the user."""
    engine = get_workflow_engine()
    username = user.get("username")
    
    if workflow_id:
        # Verify ownership
        workflow = engine.get_workflow(workflow_id)
        if not workflow or workflow.owner != username:
            raise HTTPException(403, "Access denied")
        audit = get_audit_log()
        entries = audit.get_trail(workflow_id)
        return {"entries": entries}
    else:
        # Load all user workflows to collect their IDs
        user_workflows = engine.list_workflows(owner=username)
        user_wf_ids = {w.contract_id for w in user_workflows}
        audit = get_audit_log()
        all_entries = audit.get_trail()
        filtered_entries = [e for e in all_entries if e.get("workflow_id") in user_wf_ids]
        return {"entries": filtered_entries}


@app.get("/api/privacy/transparency")
async def api_privacy_log(
    workflow_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get transparency log scoped to the user."""
    engine = get_workflow_engine()
    username = user.get("username")
    
    if workflow_id:
        # Verify ownership
        workflow = engine.get_workflow(workflow_id)
        if not workflow or workflow.owner != username:
            raise HTTPException(403, "Access denied")
        audit = get_audit_log()
        entries = audit.get_privacy_log(workflow_id)
        return {"entries": entries}
    else:
        # Load all user workflows to collect their IDs
        user_workflows = engine.list_workflows(owner=username)
        user_wf_ids = {w.contract_id for w in user_workflows}
        audit = get_audit_log()
        all_entries = audit.get_privacy_log()
        filtered_entries = [e for e in all_entries if e.get("workflow_id") in user_wf_ids]
        return {"entries": filtered_entries}


# ---------------------------------------------------------------------------
# DEMO DATA (used when Neo4j is not configured)
# ---------------------------------------------------------------------------

def _demo_dashboard(owner: Optional[str] = None):
    """Return real dashboard stats from local workflow files when Neo4j is not available."""
    engine = get_workflow_engine()
    workflows = engine.list_workflows()
    if owner:
        workflows = [w for w in workflows if w.owner == owner]

    total_contracts = len(workflows)
    vendors = set()
    flagged = 0
    approved = 0
    rejected = 0
    risk_dist = {}

    for w in workflows:
        meta = w.contract_meta
        if meta and meta.vendor_name:
            vendors.add(meta.vendor_name)
        for rf in w.risk_flags:
            flagged += 1
            cat = rf.category if hasattr(rf, 'category') else 'Other'
            risk_dist[cat] = risk_dist.get(cat, 0) + 1
        for rd in w.review_decisions:
            decision_val = rd.decision.value if hasattr(rd.decision, 'value') else str(rd.decision)
            if decision_val == "approved":
                approved += 1
            elif decision_val == "rejected":
                rejected += 1

    # Serialize workflows for the recent_uploads list
    recent = []
    for w in workflows[:10]:
        recent.append({
            "contract_id": w.contract_id,
            "status": w.status.value if hasattr(w.status, 'value') else str(w.status),
            "contract_meta": w.contract_meta.model_dump() if w.contract_meta else {},
        })

    return {
        "total_contracts": total_contracts,
        "active_vendors": len(vendors),
        "flagged_clauses": flagged,
        "approved_clauses": approved,
        "rejected_clauses": rejected,
        "risk_distribution": risk_dist,
        "recent_uploads": recent,
    }


# ---------------------------------------------------------------------------
# STATIC FILE SERVING (Frontend)
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Serve static assets
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend SPA."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    # Catch-all for SPA routing (return index.html for unknown paths)
    @app.get("/{path:path}")
    async def catch_all(path: str):
        """Serve index.html for client-side routing."""
        # Don't intercept API routes
        if path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=DEBUG)
