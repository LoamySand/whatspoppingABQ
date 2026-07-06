# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# whatspoppingABQ -- unified project image (SCRUM-22)
#
# One image, three roles, selected at `docker run`/compose time via CMD:
#   - Prefect server:   prefect server start
#   - Prefect flows:    python run_prefect_flows.py
#   - Dashboard:        streamlit run analysis/event_traffic_dashboard.py
#
# Chromium + a matching chromedriver are installed via apt (arm64-native on
# Raspberry Pi) because scrapers/visit_abq_detail_scraper.py hardcodes
# Service("/usr/bin/chromedriver") on Linux -- it does NOT fall back to
# webdriver-manager there, and webdriver-manager's downloaded binaries are
# x86_64 only anyway, so they wouldn't run on the Pi's ARM64 CPU.
# ---------------------------------------------------------------------------

FROM python:3.11-slim

# Chromium + chromedriver: apt's arm64 build gives us a matching pair for
# free, unlike downloading a driver separately and hoping the versions agree.
# python3-distutils-ish build tools not needed here -- psycopg2-binary and
# selenium both ship prebuilt wheels for arm64/amd64 on this Python version.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        curl \
    && ln -sf /usr/bin/chromium-driver /usr/bin/chromedriver \
    && rm -rf /var/lib/apt/lists/*

# Selenium launches "Chrome" by binary name; point it at the Debian chromium
# package the same way get_chrome_service()'s hardcoded driver path assumes
# a known-good binary location.
ENV CHROME_BIN=/usr/bin/chromium

WORKDIR /app

# Install Python deps in their own layer so code-only changes (the common
# case) don't invalidate the dependency layer and force a full reinstall.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Everything else. See .dockerignore for exclusions -- notably
# database/event_analytics_full.sql (~27MB) and screenshots/, which have no
# business being in a runtime image.
COPY . .

# No EXPOSE here on purpose: which port matters depends on which role this
# container is running (4200 for Prefect server, 8501 for Streamlit, none
# for the flow runner) -- that's declared per-service in docker-compose.yml
# (SCRUM-23), not baked into the image.

# No default CMD: each service in docker-compose.yml supplies its own
# command explicitly. This keeps the "what does this container do" answer
# visible in compose, rather than hidden behind an image-level default that
# some services override and others silently inherit.