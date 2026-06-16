# =============================================================================
# OpsPilot backend — multi-stage production Dockerfile
# Stage 1 builds wheels (needs compilers); Stage 2 is a slim runtime image
# that only ever runs as a non-root user.
# =============================================================================

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# Build tools + libpq headers needed to compile psycopg2 from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Only the runtime shared lib for postgres, no compilers in the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user/group to run the app as
RUN groupadd --gid 1000 opspilot \
    && useradd --uid 1000 --gid opspilot --shell /bin/bash --create-home opspilot

# Install pre-built wheels from the builder stage, then discard them
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy app source, owned by the non-root user
COPY --chown=opspilot:opspilot . .

USER opspilot

EXPOSE 8000

# Adjust the path here if your app doesn't expose /health yet —
# a simple `@app.get("/health")` returning {"status": "ok"} is enough.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
