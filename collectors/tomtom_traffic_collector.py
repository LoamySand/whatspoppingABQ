"""
TomTom Traffic API integration for baseline traffic collection.
Uses TomTom's free tier (2,500 calls/day) for systematic baseline data.
"""

import os
from dotenv import load_dotenv
import requests
import logging
from datetime import datetime
from typing import Optional, Dict
import time
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
TOMTOM_BASE_URL = "https://api.tomtom.com/traffic/services/4"


def get_traffic_flow(lat: float, lon: float, point_name: str = None) -> Optional[Dict]:
    """
    Get traffic flow data from TomTom at a specific point.
    
    Args:
        lat: Latitude
        lon: Longitude
        point_name: Optional name for logging
        
    Returns:
        Dictionary with traffic data or None if failed
    """
    if not TOMTOM_API_KEY:
        logger.error("TOMTOM_API_KEY not found in environment")
        return None
    
    # TomTom Traffic Flow API endpoint
    url = f"{TOMTOM_BASE_URL}/flowSegmentData/absolute/10/json"
    
    params = {
        'key': TOMTOM_API_KEY,
        'point': f"{lat},{lon}",
        'unit': 'MPH'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'flowSegmentData' not in data:
            logger.warning(f"No flow data returned for {point_name or (lat, lon)}")
            return None
        
        flow_data = data['flowSegmentData']
        
        # Extract relevant metrics
        current_speed = flow_data.get('currentSpeed', 0)
        free_flow_speed = flow_data.get('freeFlowSpeed', 0)
        current_travel_time = flow_data.get('currentTravelTime', 0)
        free_flow_travel_time = flow_data.get('freeFlowTravelTime', 0)
        confidence = flow_data.get('confidence', 0)
        
        # Calculate delay
        delay_seconds = current_travel_time - free_flow_travel_time
        delay_minutes = delay_seconds / 60 if delay_seconds > 0 else 0
        
        # Determine traffic level based on speed ratio
        if free_flow_speed > 0:
            speed_ratio = current_speed / free_flow_speed
            
            if speed_ratio >= 0.8:
                traffic_level = 'light'
            elif speed_ratio >= 0.6:
                traffic_level = 'moderate'
            elif speed_ratio >= 0.4:
                traffic_level = 'heavy'
            else:
                traffic_level = 'severe'
        else:
            traffic_level = 'unknown'
        
        measurement = {
            'measurement_time': datetime.now(),
            'traffic_level': traffic_level,
            'avg_speed_mph': round(current_speed, 2),
            'typical_speed_mph': round(free_flow_speed, 2),
            'travel_time_seconds': current_travel_time,
            'typical_time_seconds': free_flow_travel_time,
            'delay_minutes': round(delay_minutes, 2),
            'confidence': confidence,
            'data_source': 'tomtom',
            'raw_response': json.dumps(data)
        }
        
        logger.info(f"✓ {point_name or 'Point'}: {traffic_level}, {current_speed:.1f} mph, delay {delay_minutes:.1f} min")
        
        return measurement
        
    except requests.exceptions.RequestException as e:
        logger.error(f"TomTom API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing TomTom data: {e}")
        return None


def collect_baseline_traffic_for_venue(venue_id: int, venue_name: str,
                                       lat: float, lon: float,
                                       radius_miles: float = 1.0) -> list:
    """
    Collect baseline traffic around a venue using TomTom.
    
    Args:
        venue_id: Venue ID
        venue_name: Venue name
        lat: Venue latitude
        lon: Venue longitude
        radius_miles: Radius around venue
        
    Returns:
        List of traffic measurements
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from collectors.traffic_collector import generate_points_around_location
    
    logger.info(f"Collecting baseline traffic for: {venue_name}")
    
    # Generate 4 sample points around venue
    points = generate_points_around_location(lat, lon, radius_miles, num_points=4)
    
    measurements = []
    
    for point in points:
        # Get traffic at this point
        measurement = get_traffic_flow(
            point['lat'], 
            point['lng'],
            f"{venue_name} - {point['direction']}"
        )
        
        if measurement:
            # Add venue context
            measurement['venue_id'] = venue_id
            measurement['origin_lat'] = point['lat']
            measurement['origin_lng'] = point['lng']
            measurement['destination_lat'] = lat
            measurement['destination_lng'] = lon
            measurement['distance_miles'] = radius_miles
            measurement['is_baseline'] = True  # Flag as baseline data
            
            measurements.append(measurement)
        
        # Rate limiting (avoid hitting API too fast)
        time.sleep(0.1)
    
    logger.info(f"✓ Collected {len(measurements)} baseline measurements for {venue_name}")
    
    return measurements


if __name__ == "__main__":
    """
    Test TomTom API
    """
    print("=" * 70)
    print("TomTom Traffic API Test")
    print("=" * 70)
    print()
    
    if not TOMTOM_API_KEY:
        print("❌ TOMTOM_API_KEY not found in .env file")
        print()
        print("To get an API key:")
        print("  1. Go to https://developer.tomtom.com/")
        print("  2. Sign up for free account")
        print("  3. Create an API key")
        print("  4. Add to .env: TOMTOM_API_KEY=your_key")
        exit(1)
    
    # Test with Isotopes Park
    print("Testing traffic flow at Isotopes Park...")
    print()
    
    measurement = get_traffic_flow(
        lat=35.0781,
        lon=-106.6044,
        point_name="Isotopes Park"
    )
    
    if measurement:
        print("✓ TomTom API working!")
        print()
        print("Sample measurement:")
        for key, value in measurement.items():
            if key != 'raw_response':
                print(f"  {key}: {value}")
    else:
        print("❌ TomTom API test failed")
    
    print()
    print("=" * 70)