FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Node.js runs the official H-MEM engine (its built bridge is committed in hmem/dist); curl is for the health check.
RUN apt-get update && apt-get install -y --no-install-recommends nodejs curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s CMD curl -fs http://localhost:8765/health || exit 1

# UI at http://localhost:8765, programmatic interface at POST /run, GET /health.
# SAMPLE_MODE=true (docker run -e SAMPLE_MODE=true) needs no account and no other service.
CMD ["python", "ui/server.py", "--host", "0.0.0.0", "--port", "8765"]
