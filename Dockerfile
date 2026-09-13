# Multi-stage Dockerfile for Qualification Verification System

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Create a virtual environment and install dependencies into it
COPY . .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir "."

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

LABEL maintainer="QVS Team"
LABEL description="DevOps-Enabled Qualification Verification System"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder (includes uvicorn binary)
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Create data directory for persistent storage
RUN mkdir -p /app/data /app/uploads

# Put the venv at the front of PATH so `uvicorn` is found
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
