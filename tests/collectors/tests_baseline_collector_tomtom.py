"""Tests for collectors/baseline_collector_tomtom.py."""

from datetime import datetime

import pytest

from collectors.baseline_collector_tomtom import collect_baseline_for_venue_tomtom

pytestmark = pytest.mark.integration


class TestCollectBaselineForVenueTomtom:
    def test_successful_measurement_marked_as_baseline(self, mocker):
        mocker.patch(
            "collectors.baseline_collector_tomtom.measure_traffic_tomtom",
            return_value={
                "measurement_time": datetime.now(),
                "traffic_level": "light",
                "data_source": "tomtom",
            },
        )

        result = collect_baseline_for_venue_tomtom(
            venue_id=1, venue_name="Isotopes Park", lat=35.08, lon=-106.65, baseline_type="weekly"
        )

        assert len(result) == 1
        assert result[0]["venue_id"] == 1
        assert result[0]["is_baseline"] is True
        assert result[0]["baseline_type"] == "weekly"

    def test_failed_measurement_returns_empty_list(self, mocker):
        mocker.patch(
            "collectors.baseline_collector_tomtom.measure_traffic_tomtom",
            return_value=None,
        )

        result = collect_baseline_for_venue_tomtom(
            venue_id=1, venue_name="Nowhere", lat=0.0, lon=0.0
        )

        assert result == []

    def test_default_baseline_type_is_weekly(self, mocker):
        mocker.patch(
            "collectors.baseline_collector_tomtom.measure_traffic_tomtom",
            return_value={"measurement_time": datetime.now(), "data_source": "tomtom"},
        )

        result = collect_baseline_for_venue_tomtom(
            venue_id=2, venue_name="Some Venue", lat=35.0, lon=-106.0
        )
        assert result[0]["baseline_type"] == "weekly"

    def test_passes_coordinates_through_to_measure_traffic(self, mocker):
        mock_measure = mocker.patch(
            "collectors.baseline_collector_tomtom.measure_traffic_tomtom",
            return_value={"measurement_time": datetime.now(), "data_source": "tomtom"},
        )

        collect_baseline_for_venue_tomtom(venue_id=3, venue_name="Venue", lat=35.5, lon=-106.5)

        mock_measure.assert_called_once_with(
            origin_lat=35.5,
            origin_lng=-106.5,
            dest_lat=35.5,
            dest_lng=-106.5,
            point_name="Venue",
        )
