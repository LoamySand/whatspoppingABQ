"""
Tests for flows/ingest_events.py.

"""
from datetime import date, timedelta

import pytest

from database.db_utils import get_event_count
from flows.ingest_events import (
    generate_summary_task,
    geocode_venues_task,
    load_events_task,
    scrape_events_task,
    validate_events_task,
)

pytestmark = pytest.mark.integration


def future_date_str(days_ahead=30):
    return (date.today() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def raw_scraped_event(**overrides):
    """
    Shape of an event dict as it comes out of the scraper, i.e. BEFORE
    load_events_task/insert_events -- dates as strings, matching what
    validate_event() (in scrapers/visit_abq_detail_scraper.py) expects.
    """
    event = {
        "event_name": "Balloon Glow",
        "venue_name": "Balloon Fiesta Park",
        "event_start_date": future_date_str(),
        "category": "Festival",
    }
    event.update(overrides)
    return event


# ---------------------------------------------------------------------------
# scrape_events_task (scraper mocked)
# ---------------------------------------------------------------------------

class TestScrapeEventsTask:
    def test_returns_scraper_output(self, mocker):
        mock_scrape = mocker.patch("flows.ingest_events.scrape_events_with_details")
        mock_scrape.return_value = [raw_scraped_event(), raw_scraped_event(event_name="Chile Festival")]

        result = scrape_events_task(max_pages=2)

        mock_scrape.assert_called_once_with(max_pages=2)
        assert len(result) == 2

    def test_empty_scrape_result_does_not_error(self, mocker):
        mocker.patch("flows.ingest_events.scrape_events_with_details", return_value=[])
        result = scrape_events_task(max_pages=1)
        assert result == []


# ---------------------------------------------------------------------------
# validate_events_task (real validate_event logic, no DB involved)
# ---------------------------------------------------------------------------

class TestValidateEventsTask:
    def test_valid_future_event_passes(self):
        events = [raw_scraped_event()]
        result = validate_events_task(events)
        assert len(result) == 1

    def test_missing_event_name_is_filtered_out(self):
        events = [raw_scraped_event(event_name=None)]
        result = validate_events_task(events)
        assert result == []

    def test_missing_start_date_is_filtered_out(self):
        events = [raw_scraped_event(event_start_date=None)]
        result = validate_events_task(events)
        assert result == []

    def test_past_event_is_filtered_out(self):
        past = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        events = [raw_scraped_event(event_start_date=past)]
        result = validate_events_task(events)
        assert result == []

    def test_malformed_date_is_filtered_out(self):
        events = [raw_scraped_event(event_start_date="not-a-date")]
        result = validate_events_task(events)
        assert result == []

    def test_mixed_batch_keeps_only_valid(self):
        events = [
            raw_scraped_event(event_name="Good Event"),
            raw_scraped_event(event_name=None),
            raw_scraped_event(event_name="Also Good"),
        ]
        result = validate_events_task(events)
        names = {e["event_name"] for e in result}
        assert names == {"Good Event", "Also Good"}

    def test_empty_input_returns_empty(self):
        assert validate_events_task([]) == []


# ---------------------------------------------------------------------------
# load_events_task (real DB)
# ---------------------------------------------------------------------------

class TestLoadEventsTask:
    def test_loading_into_empty_db_reports_all_as_new(self):
        events = [
            {"event_name": "A", "venue_name": "V", "event_start_date": date.today()},
            {"event_name": "B", "venue_name": "V", "event_start_date": date.today()},
        ]
        stats = load_events_task(events)
        assert stats["events_loaded"] == 2
        assert stats["new_events"] == 2
        assert stats["updated_events"] == 0
        assert stats["total_in_db"] == 2

    def test_reloading_same_events_reports_updates_not_new(self):
        events = [{"event_name": "A", "venue_name": "V", "event_start_date": date.today()}]
        load_events_task(events)
        stats = load_events_task(events)

        assert stats["events_loaded"] == 1
        assert stats["new_events"] == 0
        assert stats["updated_events"] == 1
        assert stats["total_in_db"] == 1  # still just one row, upserted

    def test_empty_events_list(self):
        stats = load_events_task([])
        assert stats["events_loaded"] == 0
        assert stats["new_events"] == 0
        assert get_event_count() == 0


# ---------------------------------------------------------------------------
# geocode_venues_task (thin wrapper around db_utils.geocode_and_link_events,
# which already has its own tests -- just confirm the task wires it through)
# ---------------------------------------------------------------------------

class TestGeocodeVenuesTask:
    def test_delegates_to_geocode_and_link_events(self, mocker):
        mock_geocode = mocker.patch("database.db_utils.geocode_and_link_events", return_value=3)
        result = geocode_venues_task()
        assert result == 3
        mock_geocode.assert_called_once()


# ---------------------------------------------------------------------------
# generate_summary_task (real DB stats; guards against the empty-db
# division-by-zero the print statements defend against)
# ---------------------------------------------------------------------------

class TestGenerateSummaryTask:
    def test_summary_on_empty_database_does_not_raise(self):
        load_stats = {"events_loaded": 0, "new_events": 0, "updated_events": 0, "total_in_db": 0}
        summary = generate_summary_task(load_stats)
        assert summary["load_stats"] == load_stats
        assert summary["database_stats"]["total_events"] == 0
        assert summary["multi_day_count"] == 0

    def test_summary_reflects_loaded_events(self):
        load_events_task([
            {"event_name": "A", "venue_name": "V", "event_start_date": date.today(), "category": "Music"},
        ])
        load_stats = {"events_loaded": 1, "new_events": 1, "updated_events": 0, "total_in_db": 1}
        summary = generate_summary_task(load_stats)
        assert summary["database_stats"]["total_events"] == 1
        assert summary["database_stats"]["by_category"] == {"Music": 1}