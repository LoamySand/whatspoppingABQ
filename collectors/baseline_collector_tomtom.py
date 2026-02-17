"""
Baseline traffic collection using TomTom Flow API at venue location
Simplified to single point measurement for accuracy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.tomtom_flow_collector import measure_traffic_tomtom
from time import sleep
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_baseline_for_venue_tomtom(venue_id: int, venue_name: str,
                                       lat: float, lon: float,
                                       baseline_type: str = 'weekly') -> list:
    """
    Collect baseline traffic at venue location using TomTom Flow API.
    
    Single point measurement for simplicity and accuracy.
    
    Args:
        venue_id: Venue ID
        venue_name: Venue name
        lat: Venue latitude
        lon: Venue longitude
        baseline_type: Type of baseline
        
    Returns:
        List with single measurement
    """
    logger.info(f"Collecting baseline (TomTom Flow) for: {venue_name}")
    
    # Measure traffic at venue location
    measurement = measure_traffic_tomtom(
        origin_lat=lat,
        origin_lng=lon,
        dest_lat=lat,
        dest_lng=lon,
        point_name=venue_name
    )
    
    if measurement:
        # Mark as baseline
        measurement['venue_id'] = venue_id
        measurement['is_baseline'] = True
        measurement['baseline_type'] = baseline_type
        
        logger.info(f"✓ Collected 1 baseline measurement")
        
        return [measurement]
    
    logger.warning(f"No baseline data collected for {venue_name}")
    return []


if __name__ == "__main__":
    """
    Test baseline collection
    """
    print("=" * 70)
    print("TomTom Baseline Collection Test (Single Point)")
    print("=" * 70)
    print()
    
    measurements = collect_baseline_for_venue_tomtom(
        venue_id=1,
        venue_name="Isotopes Park",
        lat=35.0781,
        lon=-106.6044
    )
    
    print(f"\n✓ Collected {len(measurements)} measurements")
    
    if measurements:
        print("\nMeasurement:")
        m = measurements[0]
        for key in ['traffic_level', 'delay_minutes', 'avg_speed_mph', 'distance_miles', 'data_source']:
            print(f"  {key}: {m.get(key)}")