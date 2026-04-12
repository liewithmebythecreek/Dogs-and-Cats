FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Performance Tuning for Intel CPU
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4

# PyTorch Installation (CPU only)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# PyG Dependencies using pre-compiled CPU wheels
RUN pip install --no-cache-dir pyg-lib torch-scatter torch-sparse torch-cluster torch-geometric -f https://data.pyg.org/whl/torch-2.1.0+cpu.html

# Layer caching: install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code after dependencies to preserve cache on code change
COPY . .

# Assume models are mounted or downloaded inside /app/models
# Set PYTHONPATH to root so we can resolve backend imports
ENV PYTHONPATH=/app
ENV PORT=8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
