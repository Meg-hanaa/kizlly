"""
config.py - Central configuration for Kizlly backend.

Loads environment variables via python-dotenv and exposes typed constants
used across the entire application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file (if present)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Groq LLM Configuration
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.1"))
GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "4096"))
GROQ_MAX_RETRIES: int = int(os.getenv("GROQ_MAX_RETRIES", "5"))

# ---------------------------------------------------------------------------
# Neo4j AuraDB Configuration
# ---------------------------------------------------------------------------
NEO4J_URI: str = os.getenv("NEO4J_URI", "")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
JWT_SECRET: str = os.getenv("JWT_SECRET", "kizlly-dev-secret-change-in-production")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# ---------------------------------------------------------------------------
# Embedding Configuration
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIMENSION: int = 384

# ---------------------------------------------------------------------------
# Chunking Configuration
# ---------------------------------------------------------------------------
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
MAX_CHUNK_SENTENCES: int = 3  # Privacy: max sentences per chunk sent to Groq

# ---------------------------------------------------------------------------
# File Storage
# ---------------------------------------------------------------------------
UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
FAISS_DIR: Path = BASE_DIR / "data" / "faiss_index"
AUDIT_DB_PATH: Path = BASE_DIR / "data" / "audit.db"
WORKFLOW_DB_PATH: Path = BASE_DIR / "data" / "workflows.db"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
APP_NAME: str = "Kizlly"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = "Graph-Powered Contract Intelligence Platform"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
PORT: int = int(os.getenv("PORT", "8000"))
