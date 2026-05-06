# Dockerfile for FastAPI backend
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Use Tsinghua APT mirror for faster installs in China
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install into a wheel cache (Tsinghua PyPI mirror)
COPY requirements.txt .
RUN pip install --no-cache-dir --user \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directories owned by appuser
RUN mkdir -p /app/data/uploads /app/data/reports /app/logs \
    && chown -R appuser:appuser /app/data /app/logs

# Ensure local bin is on PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
