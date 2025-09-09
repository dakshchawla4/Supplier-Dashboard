# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# (Optional) build tools for wheels that need compiling
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/

# Upgrade pip/setuptools and install deps
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Streamlit must bind to $PORT on 0.0.0.0 in Cloud Run
ENV PORT=8080
CMD streamlit run app5.py --server.port=$PORT --server.address=0.0.0.0
