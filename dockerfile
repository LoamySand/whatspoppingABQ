# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# whatspoppingABQ -- unified project image (SCRUM-22)
#
# One image, three roles, selected at `docker run`/compose time via CMD:
#   - Prefect server:   prefect server start
#   - Prefect flows:    python run_prefect_flows.py
#   - Dashboard:        streamlit run analysis/event_traffic_dashboard.py
#
# Chromium + chromium-driver (SCRUM-66) drive
# scrapers/visit_abq_detail_scraper.py.
# ---------------------------------------------------------------------------

# Pinned to bookworm explicitly, NOT the floating python:3.11-slim tag.
# That tag previously rolled forward to Debian 13 (trixie), which pulls in a
# Chromium build new enough to hit an unresolved upstream PartitionAlloc bug
# (ENOMEM -> SIGTRAP/exit 133) on the Raspberry Pi's aarch64 kernel -- the
# reason this project ran Firefox/geckodriver for a while (SCRUM-57).
# bookworm's chromium/chromium-driver apt packages are a much older, widely
# deployed build without that issue. Production is now amd64-only (Mini PC;
# the Pi test environment was abandoned, SCRUM-24), so the bug doesn't apply
# regardless -- but staying pinned to bookworm avoids relitigating this if
# an arm64 target is ever reintroduced.
FROM python:3.11-slim-bookworm

# Chromium + chromium-driver (SCRUM-66 -- reverted from Firefox/geckodriver,
# see scrapers/visit_abq_detail_scraper.py for the driver-setup side of this).
# apt resolves the correct architecture automatically, so no arch-case logic
# is needed here the way geckodriver's direct-download install required.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
    && rm -rf /var/lib/apt/lists/*

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