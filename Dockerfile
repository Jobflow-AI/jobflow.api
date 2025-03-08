# Stage 1: Build Stage
FROM python:3.9-slim AS builder

# Set environment variables to prevent .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /jobflow-api

# Copy dependency file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Generate Prisma client
COPY db/ ./db/
RUN pip install prisma && python -c "from prisma import generate_client; generate_client()"

# Copy the rest of the application code
COPY . .

# Stage 2: Final Image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/jobflow-api \
    PATH="/usr/local/bin:$PATH"

# Install required packages for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /jobflow-api

# Copy only the installed packages and application from the builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /jobflow-api /jobflow-api
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/

# Expose the port your app runs on
EXPOSE 5001

# Add a health check endpoint
RUN echo 'from flask import Blueprint\nhealth_blueprint = Blueprint("health", __name__)\n@health_blueprint.route("/health")\ndef health_check():\n    return {"status": "healthy"}, 200' > /jobflow-api/controllers/health.py

# Use Gunicorn to run the app
CMD ["gunicorn", "--workers", "4", "--timeout", "300", "--bind", "0.0.0.0:5001", "app:app"]