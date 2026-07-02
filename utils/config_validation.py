# utils/config_validation.py
"""
Fail-fast startup config validation.

Usage:
    from utils.config_validation import validate_env
    validate_env("database", "tomtom", service_name="Traffic collector")
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Named groups of required vars, so each entry point requests only what it
# actually needs rather than every secret in the project.
#
# DB_HOST / DB_PORT / DB_NAME / DB_USER are deliberately excluded here --
# they have safe local-dev defaults in database/db_utils.py (localhost,
# 5432, postgres, postgres). DB_PASSWORD has no default and is the one
# that actually breaks things silently, so it's the only DB var enforced.
REQUIRED_VARS = {
    "database": ["DB_PASSWORD"],
    "tomtom": ["TOMTOM_API_KEY"],
    "google_maps": ["GOOGLE_MAPS_API_KEY"],
    "email_alerts": ["ALERT_EMAIL", "GMAIL_APP_PASSWORD"],
}


def validate_env(*groups: str, service_name: str = None) -> None:
    """
    Validate that all env vars required by the given groups are set and
    non-empty. Exits the process (status 1) with an itemized, human-readable
    error if anything is missing. Does nothing if everything checks out.

    Args:
        *groups: one or more keys from REQUIRED_VARS, e.g. "database", "tomtom"
        service_name: optional label shown in the error message, e.g.
            "Prefect flow server" -- helps identify which entry point failed
            when several services share a terminal/log stream.
    """
    unknown_groups = [g for g in groups if g not in REQUIRED_VARS]
    if unknown_groups:
        raise ValueError(
            f"Unknown config group(s): {unknown_groups}. "
            f"Known groups: {list(REQUIRED_VARS)}"
        )

    missing = []
    for group in groups:
        for var in REQUIRED_VARS[group]:
            value = os.getenv(var)
            if value is None or value.strip() == "":
                missing.append(var)

    if missing:
        label = f" for {service_name}" if service_name else ""
        print(f"\n[CONFIG ERROR] Missing required environment variable(s){label}:", file=sys.stderr)
        for var in missing:
            print(f"  - {var}", file=sys.stderr)
        print("\nCheck your .env file against .env.example, then retry.\n", file=sys.stderr)
        sys.exit(1)