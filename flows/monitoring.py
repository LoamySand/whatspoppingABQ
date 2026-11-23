"""
Run outcome rules and the daily rows check (WHAT-66).

The outcome functions decide whether a finished run did its job. They are
pure so the rules can be tested without Prefect, TomTom or a database.
Each returns (ok, message): ok=True pings success, ok=False pings /fail.
"""

import os
import sys

from prefect import flow

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_utils import get_connection
from utils.healthchecks import ping
from utils.logging_setup import enable_app_logging

enable_app_logging()


def event_run_outcome(result: dict) -> tuple[bool, str]:
    """
    Event traffic: nothing to collect is a healthy run. Trying to collect and
    getting zero measurements means every call failed (the 2026-08-01 outage).
    """
    attempted = result["events_collected"]
    measurements = result["measurements"]
    summary = (
        f"events checked {result['events_checked']}, collected {attempted}, "
        f"measurements {measurements}"
    )
    if attempted > 0 and measurements == 0:
        return False, f"Every collection attempt failed: {summary}"
    return True, summary


def baseline_run_outcome(result: dict) -> tuple[bool, str]:
    """
    Baseline: venue groups cover every day of the month (group 4 is days
    22-31) and every scheduled run lands on a slot, so a scheduled run that
    skips means the slot or group logic is broken (WHAT-70).
    """
    if result.get("error"):
        return False, f"Baseline collection error: {result['error']}"

    if result.get("skipped"):
        return False, f"Scheduled baseline run did not collect: {result.get('reason', '')}"

    venues = result["venues_processed"]
    measurements = result["measurements"]
    summary = f"group {result['group']}, venues {venues}, measurements {measurements}"
    if venues == 0 or measurements == 0:
        return False, f"Baseline collected nothing: {summary}"
    return True, summary


def ingestion_outcome(summary: dict) -> tuple[bool, str]:
    """Visit ABQ always lists events, so loading zero means the scrape broke."""
    loaded = summary.get("load_stats", {}).get("events_loaded", 0)
    message = f"events loaded {loaded}, geocoded venues {summary.get('geocoded_venues', 0)}"
    if loaded == 0:
        return False, f"Ingestion loaded no events: {message}"
    return True, message


def daily_rows_outcome(baseline_rows: int, event_rows: int) -> tuple[bool, str]:
    """
    Rows written in the last 24 hours. Baseline runs six times every day, so
    a day with no baseline rows means collection is down, whatever the event
    traffic did.
    """
    message = f"last 24 h: baseline rows {baseline_rows}, event rows {event_rows}"
    if baseline_rows == 0:
        return False, f"No baseline rows written in the last 24 hours: {message}"
    return True, message


def count_rows_last_24h() -> tuple[int, int]:
    """
    (baseline_rows, event_rows) created in the last 24 hours.

    created_at defaults to CURRENT_TIMESTAMP in the database session's time
    zone, so compare against LOCALTIMESTAMP from the same session.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE is_baseline),
                    COUNT(*) FILTER (WHERE is_baseline IS NOT TRUE)
                FROM traffic_measurements
                WHERE created_at >= LOCALTIMESTAMP - INTERVAL '24 hours'
                """)
            baseline_rows, event_rows = cur.fetchone()
        return baseline_rows, event_rows
    finally:
        conn.close()


@flow(name="Daily Data Check")
def daily_data_check():
    """Ping HC_PING_DAILY_ROWS with whether the pipeline wrote rows in the last day."""
    baseline_rows, event_rows = count_rows_last_24h()
    ok, message = daily_rows_outcome(baseline_rows, event_rows)
    print(f"[{'OK' if ok else 'FAIL'}] {message}")
    ping("HC_PING_DAILY_ROWS", ok=ok, message=message)
    if not ok:
        raise RuntimeError(message)
    return {"ok": ok, "baseline_rows": baseline_rows, "event_rows": event_rows}
