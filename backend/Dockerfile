FROM python:3.11-slim

WORKDIR /app

# Layer caching: install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code after dependencies to preserve cache on code change
COPY . .

# Assume models are mounted or downloaded inside /app/models
# Set PYTHONPATH to root so we can resolve backend imports
ENV PYTHONPATH=/app
ENV PORT=8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
