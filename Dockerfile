# Dockerfile for Hugging Face Spaces Deployment
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from backend folder
COPY backend/pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Copy backend app code
COPY backend/app ./app

# Copy the SQLite database to the container root (matches sqlite:///../amazon_test.db)
COPY amazon_test.db /amazon_test.db

# Add non-root user and set permissions
RUN useradd -m -u 10001 appuser && \
    chown -R appuser:appuser /app && \
    chown appuser:appuser /amazon_test.db

USER appuser

# Hugging Face Spaces run on port 7860
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2"]
