# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VENV_IN_PROJECT=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure poetry to not create virtual environment (install globally)
RUN poetry config virtualenvs.create false

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies
RUN poetry install --without dev && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Create required directories with proper permissions
RUN mkdir -p /app/uploads /app/results /app/tmp /app/logs && \
    chmod 755 /app/uploads /app/results /app/tmp /app/logs

# Set environment variables for directories
ENV UPLOAD_DIR=/app/uploads
ENV RESULTS_DIR=/app/results
ENV TEMP_DIR=/app/tmp
ENV LOG_FILE=/app/logs/ocr-backend.log

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 