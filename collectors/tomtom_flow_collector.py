"""
TomTom Traffic Flow API for consistent traffic measurements
Uses flow data at specific points for event and baseline comparison
"""

import os
from dotenv import load_dotenv
import requests
import logging
from datetime import datetime
from typing import Optional, Dict
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"


def get_traffic_flow_at_point(lat: float, lon: float, point_name: str = None) -> Optional[Dict]:
    """
    Get traffic flow data at a specific point using TomTom Traffic Flow API.
    
    This returns:
    - currentSpeed: Current speed with traffic
    - freeFlowSpeed: Speed without traffic
    - currentTravelTime: Time to traverse segment now
    - freeFlowTravelTime: Time to traverse segment without traffic
    
    Args:
        lat: Latitude
        lon: Longitude
        point_name: Optional name for logging
        
    Returns:
        Dictionary with traffic data
    """
    if not TOMTOM_API_KEY:
        logger.error("TOMTOM_API_KEY not found in environment")
        return None
    
    params = {
        'key': TOMTOM_API_KEY,
        'point': f"{lat},{lon}",
        'unit': 'MPH'
    }
    
    try:
        response = requests.get(TOMTOM_FLOW_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'flowSegmentData' not in data:
            logger.warning(f"No flow data for {point_name or (lat, lon)}")
            return None
        
        flow = data['flowSegmentData']
        
        # Extract metrics
        current_speed = flow.get('currentSpeed', 0)
        free_flow_speed = flow.get('freeFlowSpeed', 0)
        current_travel_time = flow.get('currentTravelTime', 0)
        free_flow_travel_time = flow.get('freeFlowTravelTime', 0)
        confidence = flow.get('confidence', 0)
        
        # Calculate delay in minutes
        delay_seconds = current_travel_time - free_flow_travel_time
        delay_minutes = delay_seconds / 60.0
        
        # Get segment coordinates for distance calculation
        coordinates = flow.get('coordinates', {}).get('coordinate', [])
        
        # Calculate segment distance
        if len(coordinates) >= 2:
            import math
            start = coordinates[0]
            end = coordinates[-1]
            
            lat1, lon1 = start.get('latitude', lat), start.get('longitude', lon)
            lat2, lon2 = end.get('latitude', lat), end.get('longitude', lon)
            
            # Haversine formula
            R = 3959  # Earth radius in miles
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance_miles = R * c
        else:
            # Estimate from travel time and speed
            if current_speed > 0:
                distance_miles = (current_travel_time / 3600.0) * current_speed
            else:
                distance_miles = 0
        
        # Determine traffic level
        if delay_minutes < 0.5:
            traffic_level = 'light'
        elif delay_minutes < 2:
            traffic_level = 'moderate'
        elif delay_minutes < 5:
            traffic_level = 'heavy'
        else:
            traffic_level = 'severe'
        
        measurement = {
            'measurement_time': datetime.now(),
            'traffic_level': traffic_level,
            'avg_speed_mph': round(current_speed, 2),
            'typical_speed_mph': round(free_flow_speed, 2),
            'travel_time_seconds': current_travel_time,
            'typical_time_seconds': free_flow_travel_time,
            'delay_minutes': round(delay_minutes, 2),
            'distance_miles': round(distance_miles, 2) if distance_miles > 0 else None,
            'confidence': confidence,
            'data_source': 'tomtom',
            'raw_response': json.dumps(data)
        }
        
        logger.info(f" {point_name or 'Point'}: {traffic_level}, {current_speed:.1f} mph, delay {delay_minutes:.2f} min")
        
        return measurement
        
    except requests.exceptions.RequestException as e:
        logger.error(f"TomTom Flow API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing TomTom flow data: {e}")
        import traceback
        traceback.print_exc()
        return None


def measure_traffic_tomtom(origin_lat: float, origin_lng: float,
                           dest_lat: float, dest_lng: float,
                           point_name: str = None) -> Optional[Dict]:
    """
    Measure traffic using TomTom Flow API at the origin point.
    
    This simulates a "route" measurement by getting flow data at the starting point.
    Since we're comparing event vs baseline at the same points, this is consistent.
    
    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        dest_lat: Destination latitude (for context, but we measure at origin)
        dest_lng: Destination longitude (for context)
        point_name: Optional name for logging
        
    Returns:
        Dictionary with traffic data
    """
    # Get flow at origin point
    measurement = get_traffic_flow_at_point(origin_lat, origin_lng, point_name)
    
    if measurement:
        # Add route context
        measurement['origin_lat'] = origin_lat
        measurement['origin_lng'] = origin_lng
        measurement['destination_lat'] = dest_lat
        measurement['destination_lng'] = dest_lng
        
        # If distance wasn't calculated from segment, estimate from origin to dest
        if not measurement.get('distance_miles') or measurement['distance_miles'] == 0:
            import math
            R = 3959
            dlat = math.radians(dest_lat - origin_lat)
            dlon = math.radians(dest_lng - origin_lng)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            measurement['distance_miles'] = round(R * c, 2)
    
    return measurement


if __name__ == "__main__":
    """
    Test TomTom Flow API
    """
    print("=" * 70)
    print("TomTom Traffic Flow API Test")
    print("=" * 70)
    print()
    
    if not TOMTOM_API_KEY:
        print(" TOMTOM_API_KEY not found in .env file")
        exit(1)
    
    # Test at a point
    print("Testing flow at Isotopes Park...")
    print()
    
    measurement = get_traffic_flow_at_point(
        lat=35.188087,
        lon=-106.613448,
        point_name="Known congested area"
    )
    
    if measurement:
        print(" TomTom Flow API working!")
        print()
        print("Flow data:")
        print(f"  Current speed: {measurement['avg_speed_mph']} mph")
        print(f"  Free-flow speed: {measurement['typical_speed_mph']} mph")
        print(f"  Current travel time: {measurement['travel_time_seconds']}s")
        print(f"  Free-flow travel time: {measurement['typical_time_seconds']}s")
        print(f"  DELAY: {measurement['delay_minutes']} minutes")
        print(f"  Traffic level: {measurement['traffic_level']}")
        print(f"  Distance: {measurement.get('distance_miles', 'N/A')} miles")
    else:
        print(" TomTom Flow API test failed")
    
    print()
    print("=" * 70)