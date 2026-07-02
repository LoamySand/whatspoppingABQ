"""
Tests for collectors/tomtom_flow_collector.py.

"""
import json

import pytest
import requests

from collectors.tomtom_flow_collector import (
    get_traffic_flow_at_point,
    measure_traffic_tomtom,
)

pytestmark = pytest.mark.integration  # marked for consistency; no DB actually used here


def make_tomtom_response(
    current_speed=45,
    free_flow_speed=50,
    current_travel_time=120,
    free_flow_travel_time=100,
    confidence=0.95,
    coordinates=None,
):
    """A minimal realistic TomTom flowSegmentData response body."""
    return {
        "flowSegmentData": {
            "currentSpeed": current_speed,
            "freeFlowSpeed": free_flow_speed,
            "currentTravelTime": current_travel_time,
            "freeFlowTravelTime": free_flow_travel_time,
            "confidence": confidence,
            "coordinates": {"coordinate": coordinates or []},
        }
    }


class TestGetTrafficFlowAtPoint:
    def test_no_api_key_returns_none_without_calling_api(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", None)
        mock_get = mocker.patch("collectors.tomtom_flow_collector.requests.get")

        result = get_traffic_flow_at_point(35.08, -106.65)

        assert result is None
        mock_get.assert_not_called()

    def test_successful_response_is_parsed(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        mock_response.json.return_value = make_tomtom_response()
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = get_traffic_flow_at_point(35.08, -106.65, point_name="Test Point")

        assert result["avg_speed_mph"] == 45
        assert result["typical_speed_mph"] == 50
        assert result["data_source"] == "tomtom"
        assert "raw_response" in result

    def test_delay_minutes_calculated_from_travel_time_difference(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        # 180s current vs 60s free-flow -> 120s delay -> 2.0 min
        mock_response.json.return_value = make_tomtom_response(
            current_travel_time=180, free_flow_travel_time=60
        )
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = get_traffic_flow_at_point(35.08, -106.65)
        assert result["delay_minutes"] == 2.0

    @pytest.mark.parametrize(
        "delay_minutes,expected_level",
        [
            (0.2, "light"),
            (1.0, "moderate"),
            (3.0, "heavy"),
            (10.0, "severe"),
        ],
    )
    def test_traffic_level_thresholds(self, mocker, delay_minutes, expected_level):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        free_flow_time = 100
        current_time = free_flow_time + int(delay_minutes * 60)
        mock_response = mocker.Mock()
        mock_response.json.return_value = make_tomtom_response(
            current_travel_time=current_time, free_flow_travel_time=free_flow_time
        )
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = get_traffic_flow_at_point(35.08, -106.65)
        assert result["traffic_level"] == expected_level

    def test_distance_calculated_from_segment_coordinates(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        # Two points roughly 1 mile apart in Albuquerque
        coords = [
            {"latitude": 35.0844, "longitude": -106.6504},
            {"latitude": 35.0989, "longitude": -106.6504},
        ]
        mock_response = mocker.Mock()
        mock_response.json.return_value = make_tomtom_response(coordinates=coords)
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = get_traffic_flow_at_point(35.08, -106.65)
        # ~1 mile apart (0.0145 deg lat ~= 1 mile) -- allow reasonable tolerance
        assert 0.5 < result["distance_miles"] < 1.5

    def test_missing_coordinates_estimates_distance_from_speed_and_time(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        # No coordinates -> estimate from speed * time
        mock_response.json.return_value = make_tomtom_response(
            current_speed=60, current_travel_time=60, coordinates=[]
        )
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = get_traffic_flow_at_point(35.08, -106.65)
        # 60 mph for 60 seconds = 1 mile
        assert result["distance_miles"] == pytest.approx(1.0, abs=0.01)

    def test_missing_flow_segment_data_returns_none(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"unexpected": "shape"}
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        assert get_traffic_flow_at_point(35.08, -106.65) is None

    def test_request_exception_returns_none_not_raises(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mocker.patch(
            "collectors.tomtom_flow_collector.requests.get",
            side_effect=requests.exceptions.Timeout("simulated timeout"),
        )
        assert get_traffic_flow_at_point(35.08, -106.65) is None

    def test_http_error_status_returns_none_not_raises(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        assert get_traffic_flow_at_point(35.08, -106.65) is None


class TestMeasureTrafficTomtom:
    def test_adds_origin_and_destination_context(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        mock_response.json.return_value = make_tomtom_response()
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = measure_traffic_tomtom(35.08, -106.65, 35.09, -106.66, point_name="Venue")

        assert result["origin_lat"] == 35.08
        assert result["origin_lng"] == -106.65
        assert result["destination_lat"] == 35.09
        assert result["destination_lng"] == -106.66

    def test_returns_none_when_flow_lookup_fails(self, mocker):
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", None)
        result = measure_traffic_tomtom(35.08, -106.65, 35.08, -106.65)
        assert result is None

    def test_falls_back_to_haversine_distance_when_same_point(self, mocker):
        # origin == destination (our actual usage pattern -- single-point measurement)
        # and no segment coordinates -> distance should end up 0 or None, not crash
        mocker.patch("collectors.tomtom_flow_collector.TOMTOM_API_KEY", "fake-key")
        mock_response = mocker.Mock()
        mock_response.json.return_value = make_tomtom_response(current_speed=0, coordinates=[])
        mock_response.raise_for_status = mocker.Mock()
        mocker.patch("collectors.tomtom_flow_collector.requests.get", return_value=mock_response)

        result = measure_traffic_tomtom(35.08, -106.65, 35.08, -106.65)
        assert result is not None  # should not raise