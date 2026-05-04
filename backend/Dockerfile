FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libffi-dev \
    libgdk-pixbuf-2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    chromium \
    fonts-liberation \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
# templates/ holds Jinja2 sources for the Vollbericht-PDF (full_report/) and
# the six visual SVGs (visuals/). visual_renderer.py resolves them via
# parents[1] from app/, so they must sit at /app/templates/ inside the image.
COPY templates ./templates
# static/ holds tokens.css, fonts (Sentient/Geist), full_report.css —
# referenced absolut von full_report.html via /app/static/...
COPY static ./static
# Alembic config + migration scripts must be in the image so
# `alembic upgrade head` works at container start (see
# docker-compose.yml backend service `command:` override). alembic.ini
# points at script_location = alembic which is resolved relative to
# the WORKDIR /app.
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
