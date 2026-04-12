FROM python:3.11-slim

WORKDIR /app

# ── System build dependencies ─────────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# ── Performance tuning for Intel CPU ─────────────────────────────────────────
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4

# ── Point the dynamic linker at PyTorch's bundled .so files ──────────────────
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.11/site-packages/torch/lib:$LD_LIBRARY_PATH

# ── Step 1: PyTorch 2.1.0 CPU-only (pinned version) ──────────────────────────
RUN pip install --no-cache-dir \
    torch==2.1.0 torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cpu

# ── Step 2: PyG + "Big Four" from matching pre-compiled wheel index ───────────
RUN pip install --no-cache-dir \
    torch-scatter \
    torch-sparse \
    torch-cluster \
    torch-spline-conv \
    torch-geometric \
    -f https://data.pyg.org/whl/torch-2.1.0+cpu.html

# ── Step 3: Remaining application dependencies ────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# ── Application source ────────────────────────────────────────────────────────
COPY . .

ENV PYTHONPATH=/app
ENV PORT=8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
