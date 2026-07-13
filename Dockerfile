# Production Dockerfile for Kizlly
# Multi-stage build to minimize image size

# Stage 1: Build & Cache python requirements
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final Run environment
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DEBUG=false \
    PYTHONPATH=/app/backend

# Copy cached python library dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy backend files and static frontend files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create persistent data directories
RUN mkdir -p /app/backend/data/uploads /app/backend/data/faiss_index

EXPOSE 8000

# Health check check-in configuration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start Kizlly via Gunicorn/Uvicorn runner
CMD ["python", "backend/app.py"]
