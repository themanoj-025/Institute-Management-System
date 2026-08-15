# The desktop app (CustomTkinter) requires a display and runs locally.
# This container hosts only the FastAPI REST API layer.
# Run the desktop app via: python main.py (on your local machine)

# ── Stage 1: Dependencies ──────────────────────────────────────────────
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only curl for healthcheck; remove all apt artifacts after
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      && rm -rf /var/lib/apt/lists/*

# ── Stage 2: Install Python dependencies (cached layer) ───────────────
FROM base AS dependencies
# COPY requirements.txt BEFORE COPY . . so dependency layer caches
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
      pip install --no-cache-dir -r requirements.txt

# ── Stage 3: Application code ─────────────────────────────────────────
FROM dependencies AS app
COPY . .
RUN mkdir -p database logs assets/profiles exports/generated

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
