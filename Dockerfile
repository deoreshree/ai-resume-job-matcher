# Multi-stage build for an optimized container image.
# Python version must stay compatible with requirements.txt (3.11+).
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Build dependencies for wheels that ship no binary for this platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a dedicated virtualenv that is copied forward.
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt \
    && /opt/venv/bin/python -m spacy download en_core_web_sm

# Runtime stage.
FROM python:3.11-slim

# libgomp1 is required by scikit-learn; create an unprivileged user.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=appuser:appuser . .

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

USER appuser
EXPOSE 5000

# Liveness check against the JSON health endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import os, requests; requests.get('http://localhost:%s/api/health' % os.environ.get('PORT', '5000'), timeout=5)" || exit 1

# gunicorn.conf.py honours $PORT and caps worker count.
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
