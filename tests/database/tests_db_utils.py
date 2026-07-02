"""
Tests for database/db_utils.py.

Run against a real test Postgres (see tests/conftest.py) rather than mocks,
per SCRUM-16 scoping decision. External services (geocoding API) are still
mocked -- those aren't the database's responsibility to test.
"""
from datetime import date, datetime, time

import psycopg2
import pytest

from database.db_utils import (
    clear_all_events,
    geocode_and_link_events,
    get_all_venues,
    get_category_counts,
    get_event_count,
    get_event_statistics,
    get_events_by_category,
    get_events_by_date_range,
    get_multi_day_events,
    get_recent_events,
    get_traffic_for_venue,
    get_venue_by_name,
    insert_events,
    insert_traffic_measurement,
    insert_venue,
)

pytestmark = pytest.mark.integration


def make_event(**overrides):
    """A minimally-valid event dict, matching what the scraper produces."""
    event = {
        "event_name": "Test Event",
        "venue_name": "Test Venue",
        "event_start_date": date(2026, 8, 1),
        "event_end_date": date(2026, 8, 1),
        "event_start_time": time(19, 0),
        "event_end_time": time(22, 0),
        "is_multi_day": False,
        "category": "Music",
        "sponsor": None,
        "cost_min": 10.0,
        "cost_max": 25.0,
        "cost_description": "$10-$25",
        "phone": None,
        "email": None,
        "ticket_url": None,
        "website_url": None,
        "expected_attendance": 200,
        "latitude": 35.08,
        "longitude": -106.65,
        "source_url": "https://example.com/event",
    }
    event.update(overrides)
    return event


# ---------------------------------------------------------------------------
# insert_events
# ---------------------------------------------------------------------------

class TestInsertEvents:
    def test_empty_list_returns_zero(self):
        assert insert_events([]) == 0

    def test_inserts_new_event(self):
        count = insert_events([make_event()])
        assert count == 1
        assert get_event_count() == 1

    def test_dedupes_identical_events_within_same_batch(self):
        # Same (event_name, event_start_date, venue_name) key twice
        events = [make_event(), make_event(category="Different category, same key")]
        count = insert_events(events)
        assert count == 1
        assert get_event_count() == 1

    def test_upserts_on_second_call_with_same_key(self):
        insert_events([make_event(category="Music")])
        insert_events([make_event(category="Comedy")])

        assert get_event_count() == 1  # updated in place, not duplicated
        events = get_events_by_category("Comedy")
        assert len(events) == 1

    def test_different_venue_same_name_and_date_is_a_separate_event(self):
        insert_events([make_event(venue_name="Venue A")])
        insert_events([make_event(venue_name="Venue B")])
        assert get_event_count() == 2

    def test_missing_optional_fields_default_sensibly(self):
        # Scrapers won't always populate every field
        minimal = {
            "event_name": "Bare Bones Event",
            "venue_name": "Somewhere",
            "event_start_date": date(2026, 9, 1),
        }
        count = insert_events([minimal])
        assert count == 1
        events = get_recent_events(limit=1)
        assert events[0]["event_name"] == "Bare Bones Event"


# ---------------------------------------------------------------------------
# read/query functions
# ---------------------------------------------------------------------------

class TestEventQueries:
    def test_get_event_count_empty(self):
        assert get_event_count() == 0

    def test_get_recent_events_respects_limit(self):
        insert_events([make_event(event_name=f"Event {i}", venue_name="V") for i in range(5)])
        assert len(get_recent_events(limit=3)) == 3

    def test_get_events_by_date_range(self):
        insert_events([
            make_event(event_name="In range", event_start_date=date(2026, 8, 15)),
            make_event(event_name="Out of range", event_start_date=date(2026, 12, 25)),
        ])
        results = get_events_by_date_range("2026-08-01", "2026-08-31")
        names = {e["event_name"] for e in results}
        assert names == {"In range"}

    def test_get_events_by_category(self):
        insert_events([
            make_event(event_name="Concert", category="Music"),
            make_event(event_name="Standup", category="Comedy"),
        ])
        results = get_events_by_category("Music")
        assert len(results) == 1
        assert results[0]["event_name"] == "Concert"

    def test_get_category_counts(self):
        insert_events([
            make_event(event_name="A", category="Music"),
            make_event(event_name="B", category="Music"),
            make_event(event_name="C", category="Comedy"),
        ])
        counts = get_category_counts()
        assert counts == {"Music": 2, "Comedy": 1}

    def test_get_multi_day_events_computes_duration(self):
        insert_events([make_event(
            event_name="Fiesta",
            is_multi_day=True,
            event_start_date=date(2026, 10, 1),
            event_end_date=date(2026, 10, 9),
        )])
        results = get_multi_day_events()
        assert len(results) == 1
        # +1 to include both start and end date
        assert results[0]["duration_days"] == 9

    def test_get_multi_day_events_excludes_single_day(self):
        insert_events([make_event(is_multi_day=False)])
        assert get_multi_day_events() == []


class TestEventStatistics:
    def test_stats_on_empty_database_does_not_error(self):
        stats = get_event_statistics()
        assert stats["total_events"] == 0
        assert stats["avg_cost_min"] == 0
        assert stats["avg_cost_max"] == 0
        assert stats["by_category"] == {}
        assert stats["top_venues"] == {}

    def test_stats_reflect_inserted_data(self):
        insert_events([
            make_event(event_name="A", category="Music", cost_min=10, cost_max=20, is_multi_day=False),
            make_event(event_name="B", category="Music", cost_min=0, cost_max=0, cost_description="Free"),
            make_event(event_name="C", category="Comedy", is_multi_day=True,
                       event_end_date=date(2026, 8, 3)),
        ])
        stats = get_event_statistics()
        assert stats["total_events"] == 3
        assert stats["multi_day_events"] == 1
        assert stats["free_events"] == 1  # cost_min == 0
        assert stats["by_category"] == {"Music": 2, "Comedy": 1}

    def test_free_events_counts_null_cost_with_free_in_description(self):
        insert_events([make_event(cost_min=None, cost_max=None, cost_description="Totally free!")])
        stats = get_event_statistics()
        assert stats["free_events"] == 1


class TestClearAllEvents:
    def test_clear_all_events_deletes_everything(self):
        insert_events([make_event(event_name=f"E{i}", venue_name="V") for i in range(3)])
        deleted = clear_all_events()
        assert deleted == 3
        assert get_event_count() == 0


# ---------------------------------------------------------------------------
# venues
# ---------------------------------------------------------------------------

class TestVenues:
    def test_insert_venue_returns_id(self):
        venue_id = insert_venue("The Kiva", 35.08, -106.65, address="123 Main St")
        assert isinstance(venue_id, int)

    def test_insert_venue_upserts_on_duplicate_name(self):
        id1 = insert_venue("The Kiva", 35.08, -106.65)
        id2 = insert_venue("The Kiva", 35.09, -106.66)  # updated coordinates
        assert id1 == id2

        venue = get_venue_by_name("The Kiva")
        assert float(venue["latitude"]) == 35.09

    def test_get_venue_by_name_missing_returns_none(self):
        assert get_venue_by_name("Nonexistent Venue") is None

    def test_get_all_venues_sorted_by_name(self):
        insert_venue("Zoo", 35.0, -106.0)
        insert_venue("Aquarium", 35.0, -106.0)
        venues = get_all_venues()
        assert [v["venue_name"] for v in venues] == ["Aquarium", "Zoo"]


# ---------------------------------------------------------------------------
# traffic measurements
# ---------------------------------------------------------------------------

class TestTrafficMeasurements:
    def test_insert_and_retrieve_measurement(self, make_venue):
        venue_id = make_venue()
        measurement_id = insert_traffic_measurement(
            venue_id=venue_id,
            measurement_time=datetime(2026, 8, 1, 18, 0),
            traffic_data={
                "traffic_level": "heavy",
                "avg_speed_mph": 15.0,
                "delay_minutes": 12,
                "distance_miles": 3.2,
                "data_source": "tomtom",
            },
        )
        assert isinstance(measurement_id, int)

        results = get_traffic_for_venue(venue_id)
        assert len(results) == 1
        assert results[0]["traffic_level"] == "heavy"
        assert results[0]["delay_minutes"] == 12

    def test_day_of_week_and_hour_computed_from_measurement_time(self, make_venue, db_conn):
        venue_id = make_venue()
        # Saturday, 6pm -> day_of_week convention is 0=Sun..6=Sat per the docstring
        insert_traffic_measurement(
            venue_id=venue_id,
            measurement_time=datetime(2026, 8, 1, 18, 30),  # a Saturday
            traffic_data={"data_source": "tomtom"},
        )
        with db_conn.cursor() as cur:
            cur.execute("SELECT day_of_week, hour_of_day FROM app.traffic_measurements")
            day_of_week, hour_of_day = cur.fetchone()
        assert hour_of_day == 18
        assert day_of_week == 6  # Saturday

    def test_get_traffic_for_venue_respects_limit(self, make_venue):
        venue_id = make_venue()
        for hour in range(5):
            insert_traffic_measurement(
                venue_id=venue_id,
                measurement_time=datetime(2026, 8, 1, hour, 0),
                traffic_data={"data_source": "tomtom"},
            )
        assert len(get_traffic_for_venue(venue_id, limit=2)) == 2

    def test_insert_traffic_measurement_invalid_venue_raises(self):
        with pytest.raises(psycopg2.Error):
            insert_traffic_measurement(
                venue_id=999999,  # doesn't exist -> FK violation
                measurement_time=datetime(2026, 8, 1, 12, 0),
                traffic_data={"data_source": "tomtom"},
            )


# ---------------------------------------------------------------------------
# geocode_and_link_events (external geocoding API mocked -- not the DB's job
# to test Google's API, and we don't want tests burning API quota)
# ---------------------------------------------------------------------------

class TestGeocodeAndLinkEvents:
    def test_no_venues_need_geocoding_returns_zero(self):
        insert_events([make_event(latitude=35.0, longitude=-106.0)])
        assert geocode_and_link_events() == 0

    def test_geocodes_venues_missing_coordinates(self, mocker, db_conn):
        insert_events([make_event(venue_name="Mystery Venue", latitude=None, longitude=None)])

        mock_geocode = mocker.patch("utils.geocoding.geocode_venue")
        mock_geocode.return_value = {"latitude": 35.1, "longitude": -106.1}

        geocoded_count = geocode_and_link_events()
        assert geocoded_count == 1
        mock_geocode.assert_called_once_with("Mystery Venue")

        with db_conn.cursor() as cur:
            cur.execute("SELECT latitude, longitude FROM app.events WHERE venue_name = 'Mystery Venue'")
            lat, lng = cur.fetchone()
        assert float(lat) == 35.1
        assert float(lng) == -106.1

    def test_failed_geocode_does_not_raise(self, mocker):
        insert_events([make_event(venue_name="Unfindable Venue", latitude=None, longitude=None)])
        mock_geocode = mocker.patch("utils.geocoding.geocode_venue")
        mock_geocode.return_value = None

        geocoded_count = geocode_and_link_events()
        assert geocoded_count == 0