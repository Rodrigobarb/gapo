# Multi-stage Dockerfile for Gapo
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 gapo && \
    chown -R gapo:gapo /app

USER gapo

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV GAPO_MODEL_LLM_NAME=qwen2.5:7b-instruct-q4_K_M
ENV GAPO_MODEL_TTS_MODEL=pt_BR-faber-medium
ENV GAPO_CAPTURE_FPS=3
ENV GAPO_LOG_LEVEL=INFO

# Volumes for models and data
VOLUME ["/app/data", "/home/gapo/.local/share/piper", "/home/gapo/.ollama"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import gapo; print('OK')" || exit 1

ENTRYPOINT ["gapo"]
CMD ["run"]