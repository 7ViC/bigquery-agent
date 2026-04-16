# ============================================================
# AutoAnalyst — Production Dockerfile
# Multi-stage build for minimal image size
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim AS runtime

# Security: run as non-root
RUN groupadd -r agent && useradd -r -g agent agent

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY agent/ agent/
COPY api/ api/
COPY config/settings.py config/settings.py
COPY config/logging.yaml config/logging.yaml
COPY dashboard/ dashboard/

# Set ownership
RUN chown -R agent:agent /app

USER agent

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run the API server
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
