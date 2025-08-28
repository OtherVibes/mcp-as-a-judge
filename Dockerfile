# Multi-stage build for production-ready MCP as a Judge server
FROM python:3.12-slim AS builder

# Set build arguments
ARG PORT=8050
ARG TRANSPORT=sse

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN python -m venv .venv
RUN .venv/bin/pip install uv
RUN .venv/bin/uv pip install -e .

# Production stage
FROM python:3.12-slim AS production

# Set build arguments
ARG PORT=8050
ARG TRANSPORT=sse

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=${PORT} \
    TRANSPORT=${TRANSPORT}

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY LICENSE ./

# Change ownership to non-root user
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default command
CMD ["mcp-as-a-judge"]

# Labels for metadata
LABEL org.opencontainers.image.title="MCP as a Judge" \
      org.opencontainers.image.description="AI-powered code evaluation and software engineering best practices enforcement" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Zvi Fried" \
      org.opencontainers.image.source="https://github.com/hepivax/mcp-as-a-judge" \
      org.opencontainers.image.licenses="MIT"
