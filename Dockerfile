FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for Docker cache
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend and frontend
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Create data directories
RUN mkdir -p /app/backend/data/uploads /app/backend/data/faiss_index

# Expose port (Render uses PORT env var)
EXPOSE 10000

# Start the server
CMD cd /app/backend && uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}
