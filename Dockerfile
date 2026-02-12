# ------------ Build stage: create an isolated virtualenv with deps ------------
FROM python:3.12.12 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Workdir for build artifacts
WORKDIR /app

# System deps you might need for building wheels (adjust as needed)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Create venv early to cache wheels when requirements change
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements first to maximize Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# ------------ Runtime stage: slim, non-root, copy venv + app code ------------
FROM python:3.12.12-slim

# Create a non-root user for security
ARG APP_USER=appuser
RUN useradd --create-home --shell /usr/sbin/nologin ${APP_USER}

# Install Supercronic for cron-based scheduling
# Latest releases: https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/supercronic" \
 && rm -rf /var/lib/apt/lists/*

# Set workdir and copy virtualenv from builder
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv

# Ensure the venv is first on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
# (If your repo is large, add a .dockerignore to keep the image lean.)
COPY . /app

# Optional: make sure your state directory exists for the dashboard
RUN mkdir -p /app/state && chown -R ${APP_USER}:${APP_USER} /app

USER ${APP_USER}

# --- NOTE ---
# Fly process groups (in fly.toml [processes]) WILL pass their commands at boot
# and those commands supersede CMD; ENTRYPOINT (if you set one) still runs.
# We keep a harmless default here to avoid unintended starts outside Fly.
# See: Run multiple process groups docs (process group commands supersede CMD). 
# --------------------------------------------------------------------------
CMD [ "python", "-c", "import time; print('Image ready. Waiting for Fly process command...'); time.sleep(3600)" ]
