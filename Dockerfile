# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compilation tools needed for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages system-wide (/usr/local)
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

# Stage 2: Final lightweight runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

# Install only runtime dependencies (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the builder stage
COPY --from=builder /usr/local /usr/local

# Copy application source code
COPY . .

# Create a non-privileged user and group to run securely
RUN groupadd -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup appuser && \
    chown -R appuser:appgroup /app

# Create HuggingFace cache directory with correct permissions
RUN mkdir -p /app/.hf_cache && chown -R appuser:appgroup /app/.hf_cache

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.hf_cache

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
