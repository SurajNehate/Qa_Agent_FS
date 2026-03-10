FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy source code
COPY . .

# Create data directories
RUN mkdir -p data/chroma_db

# ---------------------------------------------------------------------------
# Default: Streamlit UI (override CMD in docker-compose for FastAPI)
# ---------------------------------------------------------------------------
EXPOSE 8501 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || \
        curl --fail http://localhost:8000/api/health || exit 1

CMD ["streamlit", "run", "src/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
