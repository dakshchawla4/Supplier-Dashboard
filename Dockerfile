# Use a stable Python with prebuilt wheels available
FROM python:3.12-slim

# Make installs fast & avoid building from source
ENV PIP_ONLY_BINARY=:all: \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# (Optional) Small runtime lib used by NumPy/Polars on some platforms
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

# Upgrade pip toolchain
RUN python -m pip install --upgrade pip setuptools wheel

# Install your exact deps from wheels (fast)
RUN pip install --no-cache-dir \
    streamlit==1.36.0 \
    pandas==2.2.2 \
    polars==0.20.30 \
    openpyxl==3.1.5

# App code
WORKDIR /app
COPY . /app

# Run Streamlit, binding to Render's port
CMD ["bash","-lc","streamlit run app5.py --server.address=0.0.0.0 --server.port=${PORT:-7860}"]
