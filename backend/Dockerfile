FROM python:3.12-slim

WORKDIR /app

# System deps for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[prod]"

# Copy application code + alembic migrations
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Run alembic against Aurora if configured (no-op in dev where the SQLite
# fallback creates tables in lifespan instead). --workers 2 is safe again
# now that all routes persist to the DB rather than per-process dicts.
CMD ["sh", "-c", "if [ -n \"$AURORA_CLUSTER_ARN\" ]; then echo 'Running alembic migrations...'; alembic upgrade head; fi && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
