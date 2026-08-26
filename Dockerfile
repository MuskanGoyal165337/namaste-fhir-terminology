FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Use shell form so $PORT is expanded at runtime.
# Render injects $PORT; falls back to 8000 for local Docker usage.
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
