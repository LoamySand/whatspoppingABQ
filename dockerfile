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

# Pinned to bookworm explicitly, NOT the floating python:3.11-slim tag.
# That tag recently rolled forward to Debian 13 (trixie), which pulls in
# Chromium 150 via apt -- a build new enough to hit an unresolved upstream
# PartitionAlloc bug (ENOMEM -> SIGTRAP/exit 133 on some aarch64 kernels;
# see https://issues.chromium.org/issues/364804214, status Won't Fix /
# Not Reproducible). Confirmed on the Pi: ulimit -v and vm.overcommit_memory
# were both already fine, ruling out the usual memory-limit workarounds --
# this is the Chromium build itself, not a container config problem.
# bookworm's chromium-driver package is a much older, widely-deployed build
# without this issue.
FROM python:3.11-slim-bookworm

# Chromium + chromedriver: apt's arm64 build gives us a matching pair for
# free, unlike downloading a driver separately and hoping the versions agree.
# python3-distutils-ish build tools not needed here -- psycopg2-binary and
# selenium both ship prebuilt wheels for arm64/amd64 on this Python version.
#
# NOTE: Debian's chromium-driver package installs its binary directly at
# /usr/bin/chromedriver -- there is no separate "chromium-driver" binary to
# symlink from. (An earlier version of this Dockerfile had a `ln -sf
# /usr/bin/chromium-driver /usr/bin/chromedriver` here, which silently
# overwrote the real binary with a dangling symlink, since that source path
# never existed. Confirmed via a failing selenium.NoSuchDriverException on
# the Pi -- removed, not replaced.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        curl \
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