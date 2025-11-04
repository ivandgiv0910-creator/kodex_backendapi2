# Gunakan image Python dengan dependencies lengkap
FROM python:3.11-slim

# Set environment variable
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Tentukan working directory
WORKDIR /app

# Install OS-level dependencies (fix untuk pandas/numpy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Salin file requirements
COPY requirements.txt .

# Install dependencies Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install "httpx[http2]" --no-cache-dir || true

# Salin semua file project
COPY . .

# Set environment default
ENV APP_ENV=prod \
    HTTP2_ENABLED=false

# Buka port 8080
EXPOSE 8080

# Jalankan FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
