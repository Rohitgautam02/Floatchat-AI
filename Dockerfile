# ---- Stage 1: Frontend Build ----
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Backend + Serve ----
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend into backend/static for serving
COPY --from=frontend-build /app/frontend/build ./backend/static

# Create data directory
RUN mkdir -p ./backend/data/faiss_index ./backend/db

# Default env vars (override with docker-compose or -e)
ENV FLASK_ENV=production \
    PORT=5000

EXPOSE 5000

WORKDIR /app/backend

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "180", "app:app"]
