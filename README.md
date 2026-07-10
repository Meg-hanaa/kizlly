<img width="4320" height="1440" alt="hh26 main poster 2 with sponsors 3x1 (4320 x 1440 px) (2)" src="https://github.com/user-attachments/assets/c698b2cd-da84-4cb0-9276-125c6a7244aa" />

# Kizlly - Privacy-Preserving Contract Audit Engine

Kizlly is a local-first, privacy-respecting contract audit platform. It allows legal compliance teams and corporate reviewers to inspect, edit, and approve RAG-assisted risk analysis reports locally, preventing data leakage while mapping complex multi-vendor liabilities as an interactive relationship graph.

---

## About the Project

Kizlly is built to bridge the gap between AI capability and corporate data security. Typical legal AI systems require uploading complete, highly confidential agreements to cloud servers, risking exposure of trade secrets and compliance violations. 

Kizlly solves this by processing contracts through an isolated, multi-stage hybrid RAG pipeline:
- **Local Embedding & Chunker**: Documents are ingested locally. Text is split semantically and encoded into vector embeddings directly on the host machine using localized models, keeping the bulk of the raw contract confidential.
- **Anonymized API Audit**: Only small, isolated clause chunks containing suspected risks are sent to LLMs for classification, rate-limited and tracked inside a transparency ledger.
- **Durable Orchestration Engine**: Every step of the review process is managed by a durable workflow controller. If network connections drop or LLM limits are hit, progress is saved, allowing reviewers to resume from the exact checkpoint.
- **Relational Graph Modeling**: Approved compliance data is automatically synchronized to a Neo4j graph database, converting static legal text into a live dashboard showing active vendor risks, renewals, and liability concentrations.

---

## Problem & Domain

Describe the problem you are solving.

**Themes Selected (at least one):**
- [x] Human Experience & Productivity  
- [ ] Climate & Sustainability Systems  
- [ ] HealthTech & Bio Platforms  
- [ ] Learning & Knowledge Systems  
- [x] Work, Finance & Digital Economy  
- [ ] Infrastructure, Mobility & Smart Systems  
- [x] Trust, Identity & Security  
- [ ] Media, Social & Interactive Platforms  
- [ ] Public Systems, Governance and Civic Tech  
- [ ] Developer Tools & Software Infrastructure  

*(You can select multiple themes if applicable)*

---

## Objective

What problem does your project solve, and who does it serve?  
Clearly describe:
- **Target Users**: Corporate legal departments, procurement officers, contract managers, and independent legal reviewers.
- **Pain Point**: Manual legal review is slow, prone to missing critical liability cliffs, and sending entire contracts to public AI APIs leaks highly confidential business data.
- **Value**: Kizlly parses documents locally, extracts exact clauses, generates small RAG chunks, and performs rate-limited risk audits with localized privacy logging. It lets reviewers inspect, approve, or override flagged clause risks, mapping active vendor exposure in Neo4j.

---

## Team & Approach

### Team Name:  
`clearaura`

### Team Members:  
- **Ananya Raj** (Team Member)  
- **Meghana Ranjith** (Team Member)  

### Your Approach:
- **Why we chose this problem**: Contract management is a critical business bottleneck where privacy is paramount but currently ignored by generic AI wrapper apps.
- **Key challenges addressed**:
  - *API Rate Limiting & Network Failures*: Solved by building a durable, resume-capable workflow engine backing up intermediate execution states.
  - *Privacy Leakage*: Solved by local sentence embeddings, small-chunk context extraction, and full-audit event logging.
  - *Relational Insights*: Solved by indexing parsed agreements, dates, and risks as a graph using Neo4j to spot concentration risks instantly.

---

## Tech Stack

### Core Technologies Used:
- **Frontend**: Vanilla HTML5, CSS3, D3.js (interactive force-directed network graphs), hash-based SPA controller.
- **Backend**: FastAPI (Python 3.11), PyMuPDF / pdfplumber parser.
- **Database**: Neo4j AuraDB (graph modeling), SQLite3 (audit logging), FAISS (local vector store).
- **APIs**: Groq SDK (Llama 3.3 70B client).
- **Hosting**: Render (fully Dockerized backend service setup).

### Additional Technologies Used (Optional):
- [x] AI / ML  
- [ ] Web3 / Blockchain  
- [ ] Cyber Security 
- [x] Cloud  

---

## Sponsored Track (Optional)

Select if your project participates in any track:

- [ ] **Expo Track** – Built using Expo  
- [x] **Neo4j Track** – Uses AuraDB as primary database  
- [ ] **Base44 Track** – Prototype/Final Product built using Base44  

Provide a short note on how you used the partner technology:

> Kizlly models contracts as a graph mapping `(Contract)-[:WITH_VENDOR]->(Vendor)`, `(Contract)-[:HAS_CLAUSE]->(Clause)`, and `(Clause)-[:FLAGGED_AS]->(RiskType)`. We implement parameterized Cypher queries to compute vendor concentration blast radius, identify repeated risky clause patterns shared across vendors, and calculate renewal cascade timeline exposures.

---

## Key Features

Highlight the most important features of your project:

- **Interactive D3.js Network Graph**: Zoom, pan, drag, and click nodes (Contracts, Vendors, Clauses, Risks) to inspect relationship paths.
- **Durable Multi-Step Engine**: Retry policies on each stage (Ingest -> Embed -> Analyze -> Review -> Graph Write -> Audit). If a step fails, the pipeline pauses and restarts from the exact failed block.
- **Privacy Transparency Ledger**: An append-only SQLite log showing every character sent to external LLMs, alongside full reviewer decision logs.
- **Hinglish Legal Explainer**: Breaks down complex English legal jargon into simple, day-to-day Hinglish explanations with practical examples.

---

## Demo & Deliverables

- **Demo Video Link (Mandatory):** [Insert Link Here]  
- **Deployment Link (Recommended):** [Insert Link Here]  
- **Pitch Deck / PPT (Optional):** [Insert Link Here]  

---

## Tasks & Bonus Checklist

- [ ] All team members completed the mandatory social task  
- [ ] Bonus Task 1 – Badge sharing  
- [ ] Bonus Task 2 – Blog/article  

*(Refer to Participant Manual for details)*

---

## How to Run the Project

### Requirements:
- Python 3.10+
- A modern web browser
- A Groq API Key (for LLM contract parsing)
- A Neo4j AuraDB instance

### Local Setup:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ananyarajkamal/kizlly.git
   cd kizlly
   ```

2. **Set up Environment Variables**:
   Copy `.env.example` to `.env` in the root directory:
   ```bash
   cp .env.example .env
   ```
   Open the `.env` file and insert your credentials:
   ```env
   GROQ_API_KEY="your-groq-api-key"
   NEO4J_URI="neo4j+s://your-instance.databases.neo4j.io"
   NEO4J_USER="neo4j"
   NEO4J_PASSWORD="your-password"
   ```

3. **Install Dependencies**:
   Navigate to the backend directory and install the required Python packages:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   Start the FastAPI backend server (which also serves the static frontend dashboard):
   ```bash
   python app.py
   ```

5. **Access the Platform**:
   Open your browser and navigate to:
   *   **Main Dashboard**: [http://localhost:8000](http://localhost:8000)
   *   **API Interactive Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Future Scope

- **Fully Offline Local Execution (100% Privacy)**: Transition RAG and LLM tasks from cloud APIs to local deployment models (such as Llama-3-Legal-7B or Mistral-7B) using Ollama or vLLM to run completely offline on corporate servers.
- **Cross-Contract Precedent Matching**: Expand the FAISS vector database to match new incoming agreements against a library of approved historical corporate templates, flagging clauses that deviate from pre-approved guidelines.
- **Dynamic ER Graph Extraction**: Utilize LLM-driven entity-relation extraction to discover new node and edge categories (such as jurisdiction zones, liability limits, and indemnity conditions) and dynamically append them to the Neo4j schema.
- **Cryptographic Audit Integrity**: Append digital signatures and hashes to the SQLite audit logs to make the compliance audit ledger tamper-proof and verifiable by external regulators.
- **Autonomous Action Workflows**: Integrate webhooks to automatically trigger notifications or sync renewal tasks directly into CRM/ERP platforms (such as Salesforce, SAP, or Slack) when deadlines approach.

---

## Resources / Credits

- APIs or datasets used: Groq Llama 3.3 70B
- Open source libraries or tools referenced: PyMuPDF, FAISS, D3.js
- Acknowledgements  

---

## Final Words

This hackathon was an incredible journey of exploring the intersection of data privacy and legal automation. Building Kizlly challenged us to solve real-world problems like LLM rate-limiting and token security. 

By designing a durable state engine, we learned how to ensure that heavy document ingestion never fails mid-way. Additionally, mapping flat text contracts into a live Neo4j relational graph showed us how powerful Cypher queries can be for identifying hidden liabilities and vendor concentrations. 

We had an amazing time collaborating, prototyping, and refining the cozy custom theme. Shout-out to the HACKHAZARDS '26 team and sponsors for hosting such a productive track!

---
