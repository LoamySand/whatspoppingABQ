# collectors/tomtom_routing_collector.py
"""
TomTom Routing API with manual delay calculation
Calculates delay from speed difference rather than TomTom's reported delay
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


def measure_traffic_tomtom(origin_lat: float, origin_lng: float,
                           dest_lat: float, dest_lng: float,
                           point_name: str = None) -> Optional[Dict]:
    """
    Measure traffic using TomTom Routing API with manual delay calculation.
    
    We calculate delay ourselves:
    - Get route distance
    - Get current speed (with traffic)
    - Get free-flow speed (without traffic)
    - Calculate delay = (distance/current_speed - distance/free_flow_speed) * 60
    
    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        dest_lat: Destination latitude
        dest_lng: Destination longitude
        point_name: Optional name for logging
        
    Returns:
        Dictionary with traffic data
    """
    if not TOMTOM_API_KEY:
        logger.error("TOMTOM_API_KEY not found in environment")
        return None
    
    # TomTom Routing API
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{origin_lat},{origin_lng}:{dest_lat},{dest_lng}/json"
    
    params = {
        'key': TOMTOM_API_KEY,
        'traffic': 'true',  # Include live traffic
        'travelMode': 'car',
        'routeType': 'fastest',
        'departAt': 'now'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'routes' not in data or len(data['routes']) == 0:
            logger.warning(f"No route found for {point_name or 'route'}")
            return None
        
        route = data['routes'][0]
        summary = route['summary']
        
        # Extract metrics from TomTom
        distance_meters = summary.get('lengthInMeters', 0)
        distance_miles = distance_meters * 0.000621371
        
        travel_time_seconds = summary.get('travelTimeInSeconds', 0)
        no_traffic_time_seconds = summary.get('noTrafficTravelTimeInSeconds', travel_time_seconds)
        
        # MANUAL CALCULATION: Calculate speeds from distance and time
        if travel_time_seconds > 0:
            avg_speed_mph = (distance_miles / travel_time_seconds) * 3600
        else:
            avg_speed_mph = 0
        
        if no_traffic_time_seconds > 0:
            typical_speed_mph = (distance_miles / no_traffic_time_seconds) * 3600
        else:
            typical_speed_mph = avg_speed_mph
        
        # MANUAL CALCULATION: Delay from time difference
        delay_seconds = travel_time_seconds - no_traffic_time_seconds
        delay_minutes = delay_seconds / 60.0
        
        # Determine traffic level based on our calculated delay
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
            'avg_speed_mph': round(avg_speed_mph, 2),
            'typical_speed_mph': round(typical_speed_mph, 2),
            'travel_time_seconds': travel_time_seconds,
            'typical_time_seconds': no_traffic_time_seconds,
            'delay_minutes': round(delay_minutes, 2),
            'origin_lat': origin_lat,
            'origin_lng': origin_lng,
            'destination_lat': dest_lat,
            'destination_lng': dest_lng,
            'distance_miles': round(distance_miles, 2),
            'data_source': 'tomtom',
            'raw_response': json.dumps(data)
        }
        
        logger.info(f" {point_name or 'Route'}: {traffic_level}, {avg_speed_mph:.1f} mph, delay {delay_minutes:.2f} min ({distance_miles:.2f} mi)")
        
        return measurement
        
    except requests.exceptions.RequestException as e:
        logger.error(f"TomTom Routing API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing TomTom routing data: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    """
    Test TomTom Routing API
    """
    print("=" * 70)
    print("TomTom Routing API Test (Manual Delay Calculation)")
    print("=" * 70)
    print()
    
    if not TOMTOM_API_KEY:
        print(" TOMTOM_API_KEY not found in .env file")
        exit(1)
    
    # Test route: 1 mile north of Isotopes Park to venue
    print("Testing route...")
    print()
    
    measurement = measure_traffic_tomtom(
        origin_lat=35.0881,
        origin_lng=-106.6044,
        dest_lat=35.0781,
        dest_lng=-106.6044,
        point_name="Test Route"
    )
    
    if measurement:
        print(" TomTom Routing API working!")
        print()
        print("Measurement details:")
        print(f"  Distance: {measurement['distance_miles']} miles")
        print(f"  Current travel time: {measurement['travel_time_seconds']} seconds ({measurement['travel_time_seconds']/60:.1f} min)")
        print(f"  No-traffic time: {measurement['typical_time_seconds']} seconds ({measurement['typical_time_seconds']/60:.1f} min)")
        print(f"  Current speed: {measurement['avg_speed_mph']} mph")
        print(f"  Typical speed: {measurement['typical_speed_mph']} mph")
        print(f"  DELAY: {measurement['delay_minutes']} minutes")
        print(f"  Traffic level: {measurement['traffic_level']}")
        print()
        print("Calculation:")
        print(f"  delay = travel_time - no_traffic_time")
        print(f"  delay = {measurement['travel_time_seconds']}s - {measurement['typical_time_seconds']}s")
        print(f"  delay = {measurement['travel_time_seconds'] - measurement['typical_time_seconds']}s = {measurement['delay_minutes']:.2f} min")
    else:
        print(" TomTom Routing API test failed")
    
    print()
    print("=" * 70)