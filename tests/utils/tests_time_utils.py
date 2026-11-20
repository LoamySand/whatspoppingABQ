"""
Tests for utils/time_utils.py (WHAT-70).
"""

from datetime import UTC, datetime, timezone

import pytest

from utils import time_utils
from utils.time_utils import local_now, local_today, to_local


class TestToLocal:
    def test_winter_utc_converts_to_mst(self):
        # 2026-01-15 00:00 UTC is 2026-01-14 17:00 MST (UTC-7)
        utc = datetime(2026, 1, 15, 0, 0, tzinfo=UTC)
        assert to_local(utc) == datetime(2026, 1, 14, 17, 0)

    def test_summer_utc_converts_to_mdt(self):
        # 2026-07-15 00:00 UTC is 2026-07-14 18:00 MDT (UTC-6)
        utc = datetime(2026, 7, 15, 0, 0, tzinfo=UTC)
        assert to_local(utc) == datetime(2026, 7, 14, 18, 0)

    def test_result_is_naive(self):
        # Stored in `timestamp without time zone` columns alongside naive local rows
        assert to_local(datetime(2026, 11, 20, tzinfo=UTC)).tzinfo is None

    def test_naive_input_is_rejected(self):
        # A naive value has no defined instant, so converting it would be a guess
        with pytest.raises(ValueError):
            to_local(datetime(2026, 11, 20, 12, 0))


class TestLocalNow:
    def test_local_now_reads_utc_clock_and_converts(self, mocker):
        fake_datetime = mocker.patch.object(time_utils, "datetime", wraps=datetime)
        fake_datetime.now.return_value = datetime(2026, 11, 20, 19, 0, tzinfo=UTC)

        assert local_now() == datetime(2026, 11, 20, 12, 0)

    def test_local_today_is_the_denver_date_not_the_utc_date(self, mocker):
        # 2026-11-15 01:00 UTC is still the 14th in Denver
        fake_datetime = mocker.patch.object(time_utils, "datetime", wraps=datetime)
        fake_datetime.now.return_value = datetime(2026, 11, 15, 1, 0, tzinfo=UTC)

        assert local_today().isoformat() == "2026-11-14"
