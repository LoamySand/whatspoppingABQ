"""
Baseline traffic collection using TomTom Routing API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.tomtom_routing_collector import measure_traffic_tomtom
from collectors.traffic_collector import generate_points_around_location
from time import sleep
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_baseline_for_venue_tomtom(venue_id: int, venue_name: str,
                                       lat: float, lon: float,
                                       radius_miles: float = 1.0,
                                       baseline_type: str = 'weekly') -> list:
    """
    Collect baseline traffic using TomTom Routing API
    
    Args:
        venue_id: Venue ID
        venue_name: Venue name
        lat: Venue latitude
        lon: Venue longitude
        radius_miles: Radius around venue
        baseline_type: Type of baseline
        
    Returns:
        List of measurements
    """
    logger.info(f"Collecting baseline (TomTom Routing) for: {venue_name}")
    
    # Generate 4 sample points around venue
    points = generate_points_around_location(lat, lon, radius_miles, num_points=4)
    
    measurements = []
    
    for point in points:
        # Use TomTom Routing API
        measurement = measure_traffic_tomtom(
            origin_lat=point['lat'],
            origin_lng=point['lng'],
            dest_lat=lat,
            dest_lng=lon,
            point_name=f"{venue_name} - {point['direction']}"
        )
        
        if measurement:
            # Mark as baseline
            measurement['venue_id'] = venue_id
            measurement['is_baseline'] = True
            measurement['baseline_type'] = baseline_type
            
            measurements.append(measurement)
        
        sleep(0.2)  # Rate limiting
    
    logger.info(f"✓ Collected {len(measurements)} baseline measurements")
    
    return measurements


if __name__ == "__main__":
    """
    Test baseline collection
    """
    print("=" * 70)
    print("TomTom Baseline Collection Test (Routing API)")
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
        print("\nSample measurement:")
        m = measurements[0]
        for key in ['traffic_level', 'delay_minutes', 'avg_speed_mph', 'distance_miles', 'data_source']:
            print(f"  {key}: {m.get(key)}")