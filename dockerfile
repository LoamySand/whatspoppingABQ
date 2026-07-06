# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# whatspoppingABQ -- unified project image (SCRUM-22)
#
# One image, three roles, selected at `docker run`/compose time via CMD:
#   - Prefect server:   prefect server start
#   - Prefect flows:    python run_prefect_flows.py
#   - Dashboard:        streamlit run analysis/event_traffic_dashboard.py
#
# Firefox + geckodriver are installed via apt/direct download (see below)
# because scrapers/visit_abq_detail_scraper.py drives Firefox via geckodriver
# -- migrated from Chromium after an unresolved upstream Chromium bug caused
# reproducible crashes on the Pi's ARM64 kernel.
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

# Firefox + geckodriver (SCRUM-22 follow-up -- see scrapers/visit_abq_detail_scraper.py
# for the full explanation). Chromium 150 via apt hits an unresolved upstream
# PartitionAlloc/V8 SIGTRAP crash on the Pi's aarch64 kernel; Firefox's
# different engine/allocator isn't affected. Confirmed via extensive
# elimination on the Pi (seccomp, process model, headless mode, user
# privileges, memory ulimits, V8Sandbox, shm size all ruled out; identical
# crash persisted across every one).
#
# firefox-esr comes from Debian's apt repo (matching arch automatically).
# geckodriver does NOT have a Debian package with a Selenium-compatible
# version in bookworm's repos, so it's pulled directly from Mozilla's
# official GitHub releases instead -- pinned to a specific version (not
# "latest") so builds are reproducible and don't silently pick up a new
# geckodriver release mid-project. Architecture-aware: Mozilla publishes
# separate linux64 (amd64, e.g. Windows Docker Desktop) and linux-aarch64
# (arm64, the Pi) binaries.
ARG GECKODRIVER_VERSION=0.37.0
RUN apt-get update && apt-get install -y --no-install-recommends \
        firefox-esr \
        curl \
    && ARCH=$(dpkg --print-architecture) \
    && case "$ARCH" in \
        amd64) GECKO_ARCH="linux64" ;; \
        arm64) GECKO_ARCH="linux-aarch64" ;; \
        *) echo "Unsupported architecture for geckodriver: $ARCH" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o /tmp/geckodriver.tar.gz \
        "https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${GECKO_ARCH}.tar.gz" \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/bin geckodriver \
    && chmod +x /usr/bin/geckodriver \
    && rm /tmp/geckodriver.tar.gz \
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