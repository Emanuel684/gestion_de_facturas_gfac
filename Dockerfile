FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (gcc, pg client, tesseract OCR with Spanish language pack)
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned tag; avoid latest drift)
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system --no-cache -e .

# Copy application code
COPY . .

# Run as non-root in container
RUN useradd --create-home --shell /usr/sbin/nologin appuser && chown -R appuser:appuser /app
USER appuser

# Render (y otros PaaS) inyectan PORT; localmente usar 8000 si PORT no está definido.
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]