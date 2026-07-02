"""
Tests for collectors/tomtom_event_traffic_collector.py.

"""
from datetime import date, datetime, time, timedelta

import pytest

from collectors.tomtom_event_traffic_collector import (
    collect_traffic_for_event_tomtom,
    get_events_needing_collection,
    run_tomtom_event_collection,
    should_collect_now_tomtom,
)

pytestmark = pytest.mark.integration


def make_event(minutes_from_now=0, **overrides):
    event_datetime = datetime.now() + timedelta(minutes=minutes_from_now)
    event = {
        "event_id": 1,
        "event_name": "Test Event",
        "event_start_date": event_datetime.date(),
        "event_start_time": event_datetime.time(),
        "category": "Music",
        "venue_id": 1,
        "venue_name": "Test Venue",
        "latitude": 35.08,
        "longitude": -106.65,
    }
    event.update(overrides)
    return event


# ---------------------------------------------------------------------------
# should_collect_now_tomtom -- pure scheduling logic
# ---------------------------------------------------------------------------

class TestShouldCollectNowTomtom:
    @pytest.mark.parametrize("minutes_from_now", [-120, -90, -60, -30, 0, 30, 60, 90, 120])
    def test_collects_at_each_scheduled_point(self, minutes_from_now):
        event = make_event(minutes_from_now=minutes_from_now)
        decision = should_collect_now_tomtom(event)
        assert decision["collect"] is True
        assert decision["collection_point"] == minutes_from_now

    def test_coverage_is_continuous_between_adjacent_points_no_gap(self):
        """
        FINDING: collection_points are spaced 30 min apart with a +/-15 min
        tolerance, so adjacent windows exactly touch (15 + 15 = 30) with no
        gap. This means should_collect_now_tomtom returns collect=True
        CONTINUOUSLY for the entire -135..+135 minute range, not just at the
        9 discrete checkpoints the docstring implies. If this function is
        called more often than every 30 minutes (e.g. a 5-min cron), it will
        fire on nearly every call within that window -- worth a design
        review given the project's API-call budgeting (see run_tomtom_event_collection's
        max_calls). This test documents the actual behavior, not an
        assumption of gaps that don't exist.
        """
        for minutes_from_now in range(-134, 135, 7):  # sample across the whole range
            event = make_event(minutes_from_now=minutes_from_now)
            decision = should_collect_now_tomtom(event)
            assert decision["collect"] is True, f"expected collect=True at {minutes_from_now}min"

    def test_no_collection_just_outside_the_full_window(self):
        # 136 min is >15 from the last point (120), and there's no point beyond
        # it, so this is the first minute outside the continuously-covered range
        event = make_event(minutes_from_now=136)
        decision = should_collect_now_tomtom(event)
        assert decision["collect"] is False

    def test_does_not_collect_far_outside_window(self):
        event = make_event(minutes_from_now=300)  # 5 hours away
        decision = should_collect_now_tomtom(event)
        assert decision["collect"] is False

    def test_window_classified_as_before(self):
        event = make_event(minutes_from_now=-60)
        decision = should_collect_now_tomtom(event)
        assert decision["window"] == "before"

    def test_window_classified_as_during(self):
        event = make_event(minutes_from_now=0)
        decision = should_collect_now_tomtom(event)
        assert decision["window"] == "during"

    def test_window_classified_as_after(self):
        event = make_event(minutes_from_now=60)
        decision = should_collect_now_tomtom(event)
        assert decision["window"] == "after"

    def test_tolerance_boundary_is_inclusive_at_15_minutes(self):
        # Exactly 15 min off the "0" collection point should still collect (<=15)
        event = make_event(minutes_from_now=15)
        decision = should_collect_now_tomtom(event)
        assert decision["collect"] is True


# ---------------------------------------------------------------------------
# collect_traffic_for_event_tomtom (TomTom API mocked, DB real)
# ---------------------------------------------------------------------------

class TestCollectTrafficForEventTomtom:
    def test_successful_measurement_is_inserted(self, mocker, make_venue, db_conn):
        venue_id = make_venue(name="Isotopes Park")
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.events (event_name, venue_id, event_start_date, event_start_time)
                VALUES (%s, %s, CURRENT_DATE, %s) RETURNING event_id
                """,
                ("Baseball Game", venue_id, time(19, 0)),
            )
            (event_id,) = cur.fetchone()
        db_conn.commit()

        event = make_event(venue_id=venue_id, event_id=event_id, event_name="Baseball Game")

        mocker.patch(
            "collectors.tomtom_event_traffic_collector.measure_traffic_tomtom",
            return_value={
                "measurement_time": datetime.now(),
                "traffic_level": "moderate",
                "data_source": "tomtom",
            },
        )

        result = collect_traffic_for_event_tomtom(event)
        assert result == 1

    def test_failed_measurement_returns_zero(self, mocker, make_venue):
        venue_id = make_venue()
        event = make_event(venue_id=venue_id)

        mocker.patch(
            "collectors.tomtom_event_traffic_collector.measure_traffic_tomtom",
            return_value=None,
        )

        result = collect_traffic_for_event_tomtom(event)
        assert result == 0

    def test_db_insert_failure_returns_zero_not_raises(self, mocker):
        # venue_id doesn't exist -> FK violation inside insert_traffic_measurement,
        # which collect_traffic_for_event_tomtom should catch and report as 0
        event = make_event(venue_id=999999)

        mocker.patch(
            "collectors.tomtom_event_traffic_collector.measure_traffic_tomtom",
            return_value={
                "measurement_time": datetime.now(),
                "traffic_level": "light",
                "data_source": "tomtom",
            },
        )

        result = collect_traffic_for_event_tomtom(event)
        assert result == 0


# ---------------------------------------------------------------------------
# get_events_needing_collection (real DB)
# ---------------------------------------------------------------------------

class TestGetEventsNeedingCollection:
    def test_returns_todays_timed_events(self, db_conn, make_venue):
        venue_id = make_venue(name="Today Venue")
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.events (event_name, venue_id, event_start_date, event_start_time)
                VALUES (%s, %s, CURRENT_DATE, %s)
                """,
                ("Tonight's Show", venue_id, time(19, 0)),
            )
        db_conn.commit()

        events = get_events_needing_collection()
        assert len(events) == 1
        assert events[0]["event_name"] == "Tonight's Show"
        assert events[0]["venue_id"] == venue_id

    def test_excludes_events_without_start_time(self, db_conn, make_venue):
        venue_id = make_venue()
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.events (event_name, venue_id, event_start_date, event_start_time)
                VALUES (%s, %s, CURRENT_DATE, NULL)
                """,
                ("All-Day Event", venue_id),
            )
        db_conn.commit()

        assert get_events_needing_collection() == []

    def test_excludes_events_on_other_days(self, db_conn, make_venue):
        venue_id = make_venue()
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.events (event_name, venue_id, event_start_date, event_start_time)
                VALUES (%s, %s, CURRENT_DATE + INTERVAL '1 day', %s)
                """,
                ("Tomorrow's Show", venue_id, time(19, 0)),
            )
        db_conn.commit()

        assert get_events_needing_collection() == []

    def test_excludes_events_without_a_venue(self, db_conn):
        # venue_id is nullable on app.events, and the query INNER JOINs venue_locations
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.events (event_name, venue_id, event_start_date, event_start_time)
                VALUES (%s, NULL, CURRENT_DATE, %s)
                """,
                ("No Venue Event", time(19, 0)),
            )
        db_conn.commit()

        assert get_events_needing_collection() == []


# ---------------------------------------------------------------------------
# run_tomtom_event_collection (orchestrator; API + measurement mocked)
# ---------------------------------------------------------------------------

class TestRunTomtomEventCollection:
    def test_no_events_returns_zeroed_stats(self, mocker):
        mocker.patch(
            "collectors.tomtom_event_traffic_collector.get_events_needing_collection",
            return_value=[],
        )
        stats = run_tomtom_event_collection()
        assert stats == {
            "events_checked": 0,
            "events_collected": 0,
            "measurements_collected": 0,
            "api_calls_made": 0,
        }

    def test_skips_events_not_at_a_collection_point(self, mocker):
        # Event 15 hours away -> should_collect_now_tomtom returns collect=False
        event = make_event(minutes_from_now=900)
        mocker.patch(
            "collectors.tomtom_event_traffic_collector.get_events_needing_collection",
            return_value=[event],
        )
        mock_collect = mocker.patch(
            "collectors.tomtom_event_traffic_collector.collect_traffic_for_event_tomtom"
        )

        stats = run_tomtom_event_collection()

        mock_collect.assert_not_called()
        assert stats["events_collected"] == 0
        assert stats["events_checked"] == 1

    def test_collects_events_at_a_collection_point(self, mocker):
        event = make_event(minutes_from_now=0)
        mocker.patch(
            "collectors.tomtom_event_traffic_collector.get_events_needing_collection",
            return_value=[event],
        )
        mocker.patch(
            "collectors.tomtom_event_traffic_collector.collect_traffic_for_event_tomtom",
            return_value=1,
        )

        stats = run_tomtom_event_collection()

        assert stats["events_collected"] == 1
        assert stats["measurements_collected"] == 1

    def test_stops_at_max_calls_limit(self, mocker):
        events = [make_event(event_id=i, minutes_from_now=0) for i in range(5)]
        mocker.patch(
            "collectors.tomtom_event_traffic_collector.get_events_needing_collection",
            return_value=events,
        )
        mocker.patch(
            "collectors.tomtom_event_traffic_collector.collect_traffic_for_event_tomtom",
            return_value=1,
        )

        stats = run_tomtom_event_collection(max_calls=2)

        assert stats["api_calls_made"] <= 2