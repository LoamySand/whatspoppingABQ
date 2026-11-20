"""
Keep secrets out of log output (WHAT-69).

Exception text from HTTP clients and database drivers often carries the full
request URL or connection string. TomTom and Google Maps both take the API key
as a `key=` query parameter, so logging `f"...{e}"` wrote the key in plain
text to the container logs.

Use redact() on any exception text before it is logged, printed, written to a
file or returned in a result that ends up in a log.
"""

import os
import re

import requests

# Env vars whose values must never appear in output. Values shorter than 12
# characters are skipped so a short or placeholder value (the local default
# DB_PASSWORD is "postgres") can't blank out ordinary words. Real keys are
# longer, and the key=/password= patterns below still catch short ones.
SECRET_ENV_VARS = (
    "TOMTOM_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "DB_PASSWORD",
    "GMAIL_APP_PASSWORD",
)
_MIN_SECRET_LENGTH = 12

# key=..., api_key=..., token=..., password=... in URLs, DSNs and messages
_PARAM_PATTERN = re.compile(
    r"(?i)\b(key|api_key|apikey|access_token|token|password|passwd)=([^&\s'\"]+)"
)
# scheme://user:password@host
_URL_USERINFO_PATTERN = re.compile(r"(://[^:/@\s]+:)[^@\s]+@")

REDACTED = "REDACTED"


def redact(text: object) -> str:
    """Return str(text) with secret values and credential parameters masked."""
    result = str(text)

    for var in SECRET_ENV_VARS:
        value = os.getenv(var)
        if value and len(value) >= _MIN_SECRET_LENGTH:
            result = result.replace(value, REDACTED)

    result = _PARAM_PATTERN.sub(rf"\1={REDACTED}", result)
    result = _URL_USERINFO_PATTERN.sub(rf"\1{REDACTED}@", result)
    return result


def describe_request_error(error: requests.exceptions.RequestException) -> str:
    """
    Short description of a requests failure without the request URL.

    HTTP errors become their status code ("401 Unauthorized"); anything else
    (timeout, connection refused, ...) becomes the exception class name.
    """
    response = getattr(error, "response", None)
    if response is not None and response.status_code:
        reason = response.reason or ""
        return f"{response.status_code} {reason}".strip()
    return type(error).__name__
