"""
Secrets stay out of log output (WHAT-69).
"""

import logging

import pytest
import requests

from collectors import tomtom_flow_collector
from utils import geocoding
from utils.log_safety import describe_request_error, redact

FAKE_TOMTOM_KEY = "tt_FAKE_key_0123456789abcdefABCDEF"
FAKE_DB_PASSWORD = "s3cret-db-password"


def http_error(status: int, url: str) -> requests.exceptions.HTTPError:
    """A real HTTPError the way requests builds it, URL and all."""
    response = requests.Response()
    response.status_code = status
    response.reason = "Unauthorized" if status == 401 else "Error"
    response.url = url
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        return error
    raise AssertionError("raise_for_status did not raise")


class TestRedact:
    def test_masks_key_query_parameter(self):
        text = "401 for url: https://api.tomtom.com/x/json?key=abc123XYZ&point=35.08,-106.65"
        assert redact(text) == (
            "401 for url: https://api.tomtom.com/x/json?key=REDACTED&point=35.08,-106.65"
        )

    @pytest.mark.parametrize("param", ["api_key", "apikey", "token", "access_token", "password"])
    def test_masks_other_credential_parameters(self, param):
        assert redact(f"host=db {param}=hunter22 sslmode=require") == (
            f"host=db {param}=REDACTED sslmode=require"
        )

    def test_masks_password_in_url_userinfo(self):
        assert (
            redact("postgresql://app:pa55word@db:5432/x") == "postgresql://app:REDACTED@db:5432/x"
        )

    def test_masks_known_secret_values_in_any_format(self, monkeypatch):
        monkeypatch.setenv("DB_PASSWORD", FAKE_DB_PASSWORD)
        assert FAKE_DB_PASSWORD not in redact(f'auth failed, tried "{FAKE_DB_PASSWORD}"')

    def test_short_secret_values_are_not_used(self, monkeypatch):
        # A short value like "abc" would otherwise blank out ordinary words
        monkeypatch.setenv("DB_PASSWORD", "abc")
        assert redact("abcdef") == "abcdef"

    def test_accepts_exceptions(self):
        assert redact(ValueError("bad key=zzz")) == "bad key=REDACTED"


class TestDescribeRequestError:
    def test_http_error_becomes_status_and_reason(self):
        error = http_error(401, f"https://api.tomtom.com/x?key={FAKE_TOMTOM_KEY}")
        assert describe_request_error(error) == "401 Unauthorized"

    def test_other_errors_become_class_name(self):
        assert describe_request_error(requests.exceptions.ConnectTimeout("url ...")) == (
            "ConnectTimeout"
        )


class TestTomTomCollectorLogs:
    def test_401_logs_status_and_point_but_not_the_key(self, mocker, caplog):
        url = (
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
            f"?key={FAKE_TOMTOM_KEY}&point=35.0844%2C-106.6504&unit=MPH"
        )
        response = mocker.MagicMock()
        response.raise_for_status.side_effect = http_error(401, url)
        mocker.patch.object(tomtom_flow_collector, "TOMTOM_API_KEY", FAKE_TOMTOM_KEY)
        mocker.patch.object(tomtom_flow_collector.requests, "get", return_value=response)

        with caplog.at_level(logging.DEBUG):
            result = tomtom_flow_collector.get_traffic_flow_at_point(35.0844, -106.6504, "Venue A")

        assert result is None
        assert FAKE_TOMTOM_KEY not in caplog.text
        assert "key=" not in caplog.text
        assert "401 Unauthorized for Venue A (35.08440, -106.65040)" in caplog.text

    def test_timeout_logs_the_error_type(self, mocker, caplog):
        mocker.patch.object(tomtom_flow_collector, "TOMTOM_API_KEY", FAKE_TOMTOM_KEY)
        mocker.patch.object(
            tomtom_flow_collector.requests,
            "get",
            side_effect=requests.exceptions.ReadTimeout(f"timed out: ...?key={FAKE_TOMTOM_KEY}"),
        )

        with caplog.at_level(logging.DEBUG):
            tomtom_flow_collector.get_traffic_flow_at_point(35.0844, -106.6504, "Venue A")

        assert FAKE_TOMTOM_KEY not in caplog.text
        assert "ReadTimeout" in caplog.text


def test_geocoding_error_is_redacted(mocker, caplog):
    fake_client = mocker.MagicMock()
    fake_client.geocode.side_effect = Exception(
        "HTTP Error: 403 https://maps.googleapis.com/maps/api/geocode/json?address=x&key=AIzaFAKE123"
    )
    mocker.patch.object(geocoding, "gmaps", fake_client)

    with caplog.at_level(logging.DEBUG):
        geocoding.geocode_venue("Test Venue")

    assert "AIzaFAKE123" not in caplog.text
    assert "key=REDACTED" in caplog.text


def test_db_connection_logging_has_no_user(mocker, caplog, monkeypatch):
    import database.db_utils as db_utils

    monkeypatch.setenv("DB_USER", "postgres.projectref1234")
    mocker.patch.object(db_utils.psycopg2, "connect", return_value=mocker.MagicMock())

    with caplog.at_level(logging.DEBUG):
        db_utils.get_connection()

    assert "postgres.projectref1234" not in caplog.text
