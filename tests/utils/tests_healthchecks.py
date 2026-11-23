"""
Tests for utils/healthchecks.py (WHAT-66).
"""

import logging

import requests

from utils import healthchecks
from utils.healthchecks import ping

FAKE_URL = "https://hc-ping.com/11111111-2222-3333-4444-555555555555"


def test_success_ping_posts_message_to_the_check_url(mocker, monkeypatch):
    monkeypatch.setenv("HC_PING_BASELINE", FAKE_URL)
    post = mocker.patch.object(healthchecks.requests, "post")

    assert ping("HC_PING_BASELINE", ok=True, message="group 3, measurements 79") is True

    post.assert_called_once()
    assert post.call_args.args[0] == FAKE_URL
    assert post.call_args.kwargs["data"] == b"group 3, measurements 79"
    assert post.call_args.kwargs["timeout"] == healthchecks.TIMEOUT_SECONDS


def test_failure_ping_goes_to_the_fail_endpoint(mocker, monkeypatch):
    monkeypatch.setenv("HC_PING_BASELINE", FAKE_URL + "/")
    post = mocker.patch.object(healthchecks.requests, "post")

    ping("HC_PING_BASELINE", ok=False, message="every call failed")

    assert post.call_args.args[0] == FAKE_URL + "/fail"


def test_missing_url_skips_without_calling_out(mocker, monkeypatch, caplog):
    monkeypatch.delenv("HC_PING_BASELINE", raising=False)
    post = mocker.patch.object(healthchecks.requests, "post")

    with caplog.at_level(logging.WARNING):
        assert ping("HC_PING_BASELINE") is False

    post.assert_not_called()
    assert "HC_PING_BASELINE is not set" in caplog.text


def test_network_error_never_raises_and_never_logs_the_url(mocker, monkeypatch, caplog):
    monkeypatch.setenv("HC_PING_EVENT_TRAFFIC", FAKE_URL)
    mocker.patch.object(
        healthchecks.requests,
        "post",
        side_effect=requests.exceptions.ConnectionError(
            f"Max retries exceeded with url: {FAKE_URL}"
        ),
    )

    with caplog.at_level(logging.DEBUG):
        assert ping("HC_PING_EVENT_TRAFFIC", ok=False, message="x") is False

    assert FAKE_URL not in caplog.text
    assert "11111111-2222" not in caplog.text
    assert "ConnectionError" in caplog.text


def test_message_is_redacted_and_truncated(mocker, monkeypatch):
    monkeypatch.setenv("HC_PING_EVENT_TRAFFIC", FAKE_URL)
    post = mocker.patch.object(healthchecks.requests, "post")

    ping("HC_PING_EVENT_TRAFFIC", message="url ?key=abc123 " + "x" * 5000)

    body = post.call_args.kwargs["data"].decode()
    assert "abc123" not in body
    assert len(body) == healthchecks.MAX_MESSAGE_CHARS


def test_ping_urls_are_treated_as_secrets_by_redact(monkeypatch):
    from utils.log_safety import redact

    monkeypatch.setenv("HC_PING_DAILY_ROWS", FAKE_URL)
    assert FAKE_URL not in redact(f"posting to {FAKE_URL}")
