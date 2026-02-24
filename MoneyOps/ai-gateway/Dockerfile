# ─────────────────────────────────────────────────────────────
#  AI Gateway Dockerfile — Python FastAPI
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
