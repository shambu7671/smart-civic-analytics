# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system deps for psycopg2, OpenCV, GeoAlchemy2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.prod.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -r requirements.prod.txt --prefix=/install

# ── Stage 2: Production image ─────────────────────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="Smart Civic System"
LABEL description="AI-Based Smart Civic Issue Detection – Production Image"

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source (excludes venv, __pycache__, uploads via .dockerignore)
COPY . .

# Create non-root user for security
RUN groupadd -r smartcivic && useradd -r -g smartcivic smartcivic

# Create runtime directories with correct ownership
RUN mkdir -p uploads ai/models logs && \
    chown -R smartcivic:smartcivic /app

USER smartcivic

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production entrypoint: Gunicorn with 4 sync workers
CMD ["gunicorn", \
     "--config", "gunicorn.conf.py", \
     "wsgi:app"]
