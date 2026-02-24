# ─────────────────────────────────────────────────────────────
#  Voice Service Dockerfile — Python LiveKit Agent
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim
WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8003
CMD ["python", "-m", "app.agent.entrypoint", "start"]
