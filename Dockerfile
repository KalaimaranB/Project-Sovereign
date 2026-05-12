# Master Microservice Image for Project Sovereign
FROM python:3.13-slim-bookworm

# Set working directory
WORKDIR /app

# Prevent Python from buffering logs, providing instantaneous visual output in Compose
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Pre-seed core system dependencies often required for network/c-extension compiles
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Stage 1: Dependency Caching (Immobilize slow layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Source Ingestion
COPY . .

# Ensure custom path resolver recognizes internal 'gamespy' submodules
ENV PYTHONPATH=/app

# Default to help prompt, forcing explicit COMMAND declaration in docker-compose
CMD ["python", "--help"]
