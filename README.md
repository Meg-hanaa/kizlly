# ⚡ Kizlly — Graph-Powered Contract Intelligence Platform

> **HACKHAZARDS '26 Hackathon** | Render Workflows Track + Neo4j Track | Trust/Identity/Security Theme

Kizlly is a durable, graph-powered contract review platform that automates legal document analysis with AI-powered risk detection, human-in-the-loop approval workflows, and Neo4j-backed portfolio intelligence.

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────┐     ┌──────────────┐
│   Frontend   │────▶│              FastAPI Backend              │────▶│ Neo4j AuraDB │
│  Dashboard   │◀────│                                          │◀────│  (Graph DB)  │
└─────────────┘     │  ┌─────────────────────────────────────┐  │     └──────────────┘
                    │  │     Durable Workflow Engine          │  │
                    │  │                                     │  │     ┌──────────────┐
                    │  │  1. Ingest ──▶ 2. Embed ──▶         │  │────▶│  Groq Cloud  │
                    │  │  3. Risk Analysis ──▶                │  │     │ LLaMA 3.3 70B│
                    │  │  4. ⏸️ Human Approval ──▶            │  │     └──────────────┘
                    │  │  5. Graph Write ──▶ 6. Audit Log     │  │
                    │  └─────────────────────────────────────┘  │     ┌──────────────┐
                    │                                          │────▶│ FAISS Local  │
                    └──────────────────────────────────────────┘     │ Vector Index │
                                                                     └──────────────┘
```

## 🔒 Privacy-First Design

- **Local-first**: Full documents never leave your environment
- **Minimal API exposure**: Only 2-3 sentence chunks sent to Groq for analysis
- **Transparency**: Every chunk sent externally is logged and viewable in the UI
- **Audit trail**: Immutable, append-only log of every action and decision

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [Groq API Key](https://console.groq.com) (free tier)
- [Neo4j AuraDB](https://console.neo4j.io) (free tier, optional)

### Setup

```bash
# Clone and enter project
cd kizlly

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys

# Run the server
cd backend
python app.py
```

Open http://localhost:8000 in your browser.

### Demo Credentials
- Username: `admin`
- Password: `admin123`

## 📊 Neo4j Graph Data Model

```
(Contract)-[:WITH_VENDOR]->(Vendor)
(Contract)-[:HAS_CLAUSE]->(Clause)-[:FLAGGED_AS]->(RiskType)
(Contract)-[:RENEWS_ON]->(Date)
(Vendor)-[:APPEARS_IN]->(Contract)
```

### Graph Queries Power the Dashboard
- **Vendor Exposure**: Cross-contract concentration risk
- **Renewal Cascade**: Contracts renewing in 30/60/90 day windows
- **Clause Patterns**: Repeated risky clause types across vendors

## 🔄 Durable Workflow (Render Workflows Pattern)

Each step is independently retryable and resumable:

| Step | Retry Policy | Description |
|------|-------------|-------------|
| 1. Ingest | 3 retries | Parse PDF/DOCX, extract text |
| 2. Embed & Search | 2 retries | Chunk + embed + FAISS index |
| 3. Risk Analysis | 5 retries | Groq LLaMA risk detection |
| 4. Human Approval | ∞ (pauses) | Reviewer approves/rejects clauses |
| 5. Graph Write | 3 retries | Write to Neo4j AuraDB |
| 6. Audit Log | 1 retry | Finalize immutable audit trail |

## 🛡️ Trust & Security

- **Reviewer Identity**: JWT auth ties every decision to a user
- **Audit Trail**: Immutable, append-only SQLite log
- **Privacy Transparency**: UI shows exactly what data was sent to AI
- **Disclaimer**: "Decision support only — not legal advice"

## 📦 Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

Uses `render.yaml` Blueprint for one-click deployment.

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (Python) |
| LLM | Groq LLaMA 3.3 70B |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Search | FAISS (local) |
| Graph DB | Neo4j AuraDB |
| Workflow | Durable engine (Render Workflows pattern) |
| Frontend | Vanilla HTML/CSS/JS + D3.js |
| Auth | JWT |
| Deployment | Render (Docker) |

## ⚠️ Disclaimer

Kizlly is a **decision support tool** — not legal advice. AI-generated risk flags are suggestions based on pattern analysis. Always consult qualified legal counsel for contract decisions.

---

Built for **HACKHAZARDS '26** 🏆
