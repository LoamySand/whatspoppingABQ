"""
Collection timing uses America/Denver, not the container clock (WHAT-70).

The prefect-flows container runs in UTC. Before WHAT-70, baseline slot
matching, venue-group rotation and event collection points all read naive
datetime.now(), so they ran on UTC time. These tests pin the clock through
local_now() and check the decisions are made in Denver time.
"""

from datetime import date, datetime, time

import pytest

from collectors import baseline_schedule, tomtom_event_traffic_collector
from collectors.baseline_schedule import get_current_baseline_group, should_collect_baseline_now
from collectors.tomtom_event_traffic_collector import should_collect_now_tomtom


def freeze_local(mocker, module, moment: datetime):
    mocker.patch.object(module, "local_now", return_value=moment)


class TestBaselineSlots:
    @pytest.mark.parametrize(
        "moment",
        [
            datetime(2026, 11, 18, 17, 5),  # MST date
            datetime(2026, 7, 16, 17, 5),  # MDT date
        ],
    )
    def test_17_local_matches_the_17_slot_in_both_mst_and_mdt(self, mocker, moment):
        freeze_local(mocker, baseline_schedule, moment)

        should_collect, _group, slot = should_collect_baseline_now()

        assert should_collect is True
        assert slot == "17:00"

    @pytest.mark.parametrize("hour", [7, 12, 17, 19, 21, 23])
    def test_every_scheduled_run_hour_matches_a_slot(self, mocker, hour):
        # run_prefect_flows.py fires baseline at these America/Denver hours.
        # Before WHAT-70 only one of the six matched once converted to UTC.
        freeze_local(mocker, baseline_schedule, datetime(2026, 11, 18, hour, 0))

        should_collect, _group, slot = should_collect_baseline_now()

        assert should_collect is True
        assert slot == f"{hour:02d}:00"

    def test_off_slot_local_time_does_not_collect(self, mocker):
        freeze_local(mocker, baseline_schedule, datetime(2026, 11, 18, 10, 0))

        should_collect, _group, slot = should_collect_baseline_now()

        assert should_collect is False
        assert slot is None


class TestBaselineGroup:
    def test_group_follows_the_denver_date_not_the_utc_date(self, mocker):
        # 2026-11-14 18:00 MST is already the 15th in UTC (group 3);
        # in Denver it's still the 14th, so group 2.
        freeze_local(mocker, baseline_schedule, datetime(2026, 11, 14, 18, 0))

        assert get_current_baseline_group() == 2


class TestEventCollectionPoints:
    def make_event(self, start: datetime) -> dict:
        return {
            "event_id": 1,
            "event_name": "Evening Show",
            "event_start_date": start.date(),
            "event_start_time": start.time(),
            "category": "Music",
            "venue_id": 1,
            "venue_name": "Test Venue",
            "latitude": 35.08,
            "longitude": -106.65,
        }

    def test_event_start_in_local_time_is_collection_point_zero(self, mocker):
        start = datetime(2026, 11, 18, 19, 0)
        freeze_local(mocker, tomtom_event_traffic_collector, start)

        decision = should_collect_now_tomtom(self.make_event(start))

        assert decision["collect"] is True
        assert decision["collection_point"] == 0
        assert decision["window"] == "during"

    def test_noon_local_is_not_a_collection_point_for_a_19_00_event(self, mocker):
        # Before WHAT-70 a 19:00 MT event got its "during" sample at 19:00 UTC,
        # which is 12:00 MST. That must no longer collect.
        freeze_local(mocker, tomtom_event_traffic_collector, datetime(2026, 11, 18, 12, 0))

        decision = should_collect_now_tomtom(self.make_event(datetime(2026, 11, 18, 19, 0)))

        assert decision["collect"] is False

    def test_collector_queries_the_local_date(self, mocker):
        mocker.patch.object(
            tomtom_event_traffic_collector, "local_today", return_value=date(2026, 11, 14)
        )
        fake_conn = mocker.MagicMock()
        mocker.patch.object(
            tomtom_event_traffic_collector, "get_connection", return_value=fake_conn
        )
        cursor = fake_conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []

        tomtom_event_traffic_collector.get_events_needing_collection()

        sql, params = cursor.execute.call_args.args
        assert "CURRENT_DATE" not in sql
        assert params == (date(2026, 11, 14),)


def test_measurement_time_is_local(mocker):
    # measurement_time drives hour_of_day / day_of_week in insert_traffic_measurement
    from collectors import tomtom_flow_collector

    mocker.patch.object(tomtom_flow_collector, "TOMTOM_API_KEY", "fake-key")
    mocker.patch.object(
        tomtom_flow_collector, "local_now", return_value=datetime(2026, 11, 18, 12, 0)
    )
    response = mocker.MagicMock()
    response.json.return_value = {
        "flowSegmentData": {
            "currentSpeed": 30,
            "freeFlowSpeed": 35,
            "currentTravelTime": 60,
            "freeFlowTravelTime": 50,
            "confidence": 1,
            "coordinates": {"coordinate": []},
        }
    }
    mocker.patch.object(tomtom_flow_collector.requests, "get", return_value=response)

    result = tomtom_flow_collector.get_traffic_flow_at_point(35.08, -106.65)

    assert result["measurement_time"] == datetime(2026, 11, 18, 12, 0)
    assert result["measurement_time"].time() == time(12, 0)
