# Stage 1: Build Stage
FROM python:3.9.18-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies including PyMuPDF requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmupdf-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /jobflow-api

# Copy dependency file and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir && \
    pip install gunicorn && \
    pip install uvicorn  # Add explicit uvicorn installation

# Generate Prisma client (Fixed command)
COPY db/ ./db/
COPY prisma/ ./prisma/
RUN pip install prisma && \
    prisma generate --schema=prisma/schema.prisma && \
    prisma py fetch  

# Copy the rest of the application code
COPY . .

# Stage 2: Final Image
FROM python:3.9.18-slim

# Install runtime dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

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
# Copy gunicorn and uvicorn binaries specifically
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/

# Expose the port your app runs on
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]