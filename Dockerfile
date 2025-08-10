# Multi-platform support (supports both x86_64 and ARM64/Apple Silicon)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for multi-platform support
ENV TORCH_DEVICE=auto
ENV TRANSFORMERS_CACHE=/app/.cache/transformers
ENV HF_HOME=/app/.cache/huggingface

# Create cache directories
RUN mkdir -p /app/.cache/transformers /app/.cache/huggingface

# Copy requirements first for better caching
COPY requirements.txt .

# Install PyTorch with multi-platform support
RUN pip install --no-cache-dir torch>=2.1.0 --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]