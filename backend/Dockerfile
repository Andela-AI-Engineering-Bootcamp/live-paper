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

# Copy application code
COPY app/ app/

# Non-root user
# RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
