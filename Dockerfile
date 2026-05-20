# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv
RUN pip install --no-cache-dir uv==0.2.36

COPY pyproject.toml .
COPY app/ app/

# Install production dependencies into an isolated prefix
RUN uv pip install --system --no-cache-dir .

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user
RUN groupadd --gid 1001 botuser && \
    useradd --uid 1001 --gid botuser --shell /bin/bash --create-home botuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=botuser:botuser app/ app/

# Data directory for SQLite (will be a named volume in compose)
RUN mkdir -p /app/data && chown botuser:botuser /app/data

USER botuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/app/data/birthday_guard.db

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import asyncio, aiosqlite, os; asyncio.run(aiosqlite.connect(os.getenv('DB_PATH', '/app/data/birthday_guard.db')))" || exit 1

CMD ["python", "-m", "app.main"]
