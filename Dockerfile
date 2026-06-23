FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=1000

WORKDIR /app

# System deps for building some wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# 1) Upgrade pip and install CPU-only torch first from the official PyTorch index
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu \
 && pip install --no-cache-dir --default-timeout=1000 --retries 10 -r /app/requirements.txt

COPY app /app/app
COPY dashboard /app/dashboard

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
