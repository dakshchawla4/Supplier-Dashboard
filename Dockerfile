# Dockerfile (replace the current file with this)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# (Optional) build tools for wheels that need compiling
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (cached layer)
COPY requirements.txt /app/

# Upgrade pip/setuptools and install deps
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . /app

# Do not hardcode the PORT here (let the platform provide it).
# Use a shell-based CMD so $PORT is expanded at container runtime.
# Replace app5.py with your main app file if different.
CMD ["sh", "-c", "streamlit run app5.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false"]

