"""
Healthchecks.io push checks (WHAT-66).

Each scheduled flow pings its own check when it finishes. A missing ping
(container down, flow never ran, flow crashed before pinging) turns the
check red when its period plus grace expires. A run that ran but did not do
its job pings /fail, which alerts immediately.

Ping URLs live in env vars (see CHECKS) and are treated as secrets: anyone
with the URL can send fake pings, so the URL is never logged.
"""

import logging
import os

import requests

from utils.log_safety import describe_request_error, redact

logger = logging.getLogger(__name__)

# Env var -> what it monitors. Keep in sync with config_validation's
# "healthchecks" group and .env.example.
CHECKS = {
    "HC_PING_EVENT_TRAFFIC": "Event traffic collection (every 30 min)",
    "HC_PING_BASELINE": "Baseline traffic collection (6 slots/day)",
    "HC_PING_INGESTION": "Weekly event ingestion",
    "HC_PING_DAILY_ROWS": "Daily rows-written check",
}

TIMEOUT_SECONDS = 5
# Healthchecks stores up to 100 kB of request body per ping; keep it short
MAX_MESSAGE_CHARS = 2000


def ping(check_var: str, ok: bool = True, message: str = "") -> bool:
    """
    Send a success (ok=True) or /fail (ok=False) ping for one check.

    The message is sent as the request body and shows in the check's event
    log on Healthchecks.io. Never raises: a monitoring outage must not break
    collection. Returns True if the ping was delivered.
    """
    url = os.getenv(check_var, "").strip()
    if not url:
        logger.warning(f"{check_var} is not set; skipping Healthchecks ping")
        return False

    target = url.rstrip("/") + ("" if ok else "/fail")
    body = redact(message)[:MAX_MESSAGE_CHARS]

    try:
        response = requests.post(target, data=body.encode("utf-8"), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Healthchecks ping for {check_var} failed: {describe_request_error(e)}")
        return False

    logger.info(f"Healthchecks ping sent: {check_var} {'ok' if ok else 'FAIL'}")
    return True
