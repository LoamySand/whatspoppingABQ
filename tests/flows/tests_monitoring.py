"""
Run outcome rules and flow wiring for Healthchecks.io (WHAT-66).
"""

import pytest

from flows import collect_traffic, monitoring
from flows.monitoring import (
    baseline_run_outcome,
    daily_rows_outcome,
    event_run_outcome,
    ingestion_outcome,
)


class TestEventRunOutcome:
    def test_nothing_to_collect_is_healthy(self):
        ok, _ = event_run_outcome(
            {"events_checked": 0, "events_collected": 0, "measurements": 0, "api_calls": 0}
        )
        assert ok is True

    def test_events_found_but_none_in_window_is_healthy(self):
        ok, _ = event_run_outcome(
            {"events_checked": 4, "events_collected": 0, "measurements": 0, "api_calls": 0}
        )
        assert ok is True

    def test_collected_rows_is_healthy(self):
        ok, message = event_run_outcome(
            {"events_checked": 2, "events_collected": 2, "measurements": 2, "api_calls": 2}
        )
        assert ok is True
        assert "measurements 2" in message

    def test_attempts_with_zero_measurements_fail(self):
        # The 2026-08-01 outage: every TomTom call returned 401
        ok, message = event_run_outcome(
            {"events_checked": 3, "events_collected": 3, "measurements": 0, "api_calls": 0}
        )
        assert ok is False
        assert "Every collection attempt failed" in message


class TestBaselineRunOutcome:
    def test_collected_rows_is_healthy(self):
        ok, _ = baseline_run_outcome(
            {"group": 3, "venues_processed": 79, "measurements": 79, "api_calls": 79}
        )
        assert ok is True

    def test_all_calls_failing_fails(self):
        ok, message = baseline_run_outcome(
            {"group": 3, "venues_processed": 79, "measurements": 0, "api_calls": 0}
        )
        assert ok is False
        assert "collected nothing" in message

    def test_no_venues_fails(self):
        ok, _ = baseline_run_outcome(
            {"group": 3, "venues_processed": 0, "measurements": 0, "api_calls": 0}
        )
        assert ok is False

    def test_skip_during_a_scheduled_run_fails(self):
        # Before WHAT-70, five of six runs skipped like this every day
        ok, message = baseline_run_outcome({"skipped": True, "reason": "Not collection time"})
        assert ok is False
        assert "Not collection time" in message

    def test_error_fails(self):
        ok, message = baseline_run_outcome({"error": "connection refused"})
        assert ok is False
        assert "connection refused" in message


class TestIngestionOutcome:
    def test_events_loaded_is_healthy(self):
        ok, _ = ingestion_outcome({"load_stats": {"events_loaded": 120}, "geocoded_venues": 3})
        assert ok is True

    def test_zero_events_loaded_fails(self):
        ok, message = ingestion_outcome({"load_stats": {"events_loaded": 0}})
        assert ok is False
        assert "loaded no events" in message


class TestDailyRowsOutcome:
    def test_baseline_rows_is_healthy_even_without_events(self):
        assert daily_rows_outcome(baseline_rows=79, event_rows=0)[0] is True

    def test_no_baseline_rows_fails_even_with_event_rows(self):
        ok, message = daily_rows_outcome(baseline_rows=0, event_rows=12)
        assert ok is False
        assert "No baseline rows" in message


@pytest.mark.integration
class TestCountRowsLast24h:
    def test_counts_only_recent_rows_by_type(self, db_conn, make_venue):
        venue_id = make_venue(name="Count Venue")
        with db_conn.cursor() as cur:
            for is_baseline, age in [
                (True, "1 hour"),
                (True, "2 hours"),
                (False, "3 hours"),
                (True, "30 hours"),  # outside the window
            ]:
                cur.execute(
                    """
                    INSERT INTO app.traffic_measurements
                        (venue_id, measurement_time, data_source, is_baseline, created_at)
                    VALUES (%s, LOCALTIMESTAMP, 'tomtom', %s, LOCALTIMESTAMP - %s::interval)
                    """,
                    (venue_id, is_baseline, age),
                )
        db_conn.commit()

        assert monitoring.count_rows_last_24h() == (2, 1)


class TestFlowWiring:
    """The flows ping with the outcome and fail the Prefect run when it's bad."""

    def test_event_flow_pings_fail_and_raises_when_every_call_failed(self, mocker):
        mocker.patch.object(
            collect_traffic,
            "run_tomtom_event_collection",
            return_value={
                "events_checked": 2,
                "events_collected": 2,
                "measurements_collected": 0,
                "api_calls_made": 0,
            },
        )
        ping = mocker.patch.object(collect_traffic, "ping")

        with pytest.raises(RuntimeError, match="Every collection attempt failed"):
            collect_traffic.event_traffic_flow()

        ping.assert_called_once()
        assert ping.call_args.args[0] == "HC_PING_EVENT_TRAFFIC"
        assert ping.call_args.kwargs["ok"] is False

    def test_event_flow_pings_success_when_nothing_to_collect(self, mocker):
        mocker.patch.object(
            collect_traffic,
            "run_tomtom_event_collection",
            return_value={
                "events_checked": 0,
                "events_collected": 0,
                "measurements_collected": 0,
                "api_calls_made": 0,
            },
        )
        ping = mocker.patch.object(collect_traffic, "ping")

        collect_traffic.event_traffic_flow()

        assert ping.call_args.kwargs["ok"] is True

    def test_baseline_flow_pings_success_after_collecting(self, mocker):
        mocker.patch.object(
            collect_traffic,
            "run_baseline_collection",
            return_value={
                "collected": True,
                "group": 3,
                "venues_processed": 79,
                "measurements_collected": 79,
                "api_calls_made": 79,
            },
        )
        ping = mocker.patch.object(collect_traffic, "ping")

        collect_traffic.baseline_traffic_flow()

        assert ping.call_args.args[0] == "HC_PING_BASELINE"
        assert ping.call_args.kwargs["ok"] is True

    def test_baseline_flow_passes_collector_errors_to_the_fail_ping(self, mocker):
        mocker.patch.object(
            collect_traffic,
            "run_baseline_collection",
            return_value={"collected": False, "error": "connection refused"},
        )
        ping = mocker.patch.object(collect_traffic, "ping")

        with pytest.raises(RuntimeError, match="connection refused"):
            collect_traffic.baseline_traffic_flow()

        assert ping.call_args.kwargs["ok"] is False

    def test_daily_check_pings_fail_and_raises_with_no_baseline_rows(self, mocker):
        mocker.patch.object(monitoring, "count_rows_last_24h", return_value=(0, 5))
        ping = mocker.patch.object(monitoring, "ping")

        with pytest.raises(RuntimeError, match="No baseline rows"):
            monitoring.daily_data_check()

        assert ping.call_args.args[0] == "HC_PING_DAILY_ROWS"
        assert ping.call_args.kwargs["ok"] is False
