"""
Traffic data collector using Google Maps Distance Matrix API.
Collects traffic conditions around event venues.
"""

import os
from dotenv import load_dotenv
import googlemaps
import logging
from datetime import datetime
from typing import Optional, Dict, List
import json

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Google Maps client
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    logger.warning("GOOGLE_MAPS_API_KEY not found in environment variables")
    gmaps = None
else:
    gmaps = googlemaps.Client(key=API_KEY)


def collect_traffic_around_venue(venue_lat: float, venue_lng: float, 
                                 radius_miles: float = 1.0,
                                 num_points: int = 4) -> List[Dict]:
    """
    Collect traffic data around a venue by measuring to/from nearby points.
    
    Strategy: Create a circle of points around the venue and measure
    traffic from each point to the venue.
    
    Args:
        venue_lat: Venue latitude
        venue_lng: Venue longitude
        radius_miles: Radius around venue to sample (default 1 mile)
        num_points: Number of sample points around venue (default 4)
        
    Returns:
        List of traffic measurement dictionaries
    """
    if not gmaps:
        logger.error("Google Maps client not initialized")
        return []
    
    # Generate points around venue (N, S, E, W, or more)
    sample_points = generate_points_around_location(
        venue_lat, venue_lng, radius_miles, num_points
    )
    
    measurements = []
    
    for i, point in enumerate(sample_points, 1):
        logger.info(f"Measuring traffic from point {i}/{len(sample_points)}")
        
        measurement = measure_traffic(
            origin_lat=point['lat'],
            origin_lng=point['lng'],
            dest_lat=venue_lat,
            dest_lng=venue_lng
        )
        
        if measurement:
            measurements.append(measurement)
    
    return measurements


def measure_traffic(origin_lat: float, origin_lng: float,
                   dest_lat: float, dest_lng: float) -> Optional[Dict]:
    """
    Measure traffic between two points using Distance Matrix API.
    
    Args:
        origin_lat, origin_lng: Starting point coordinates
        dest_lat, dest_lng: Destination coordinates
        
    Returns:
        Dictionary with traffic data or None if failed
    """
    if not gmaps:
        logger.error("Google Maps client not initialized")
        return None
    
    try:
        # Create coordinate strings
        origin = f"{origin_lat},{origin_lng}"
        destination = f"{dest_lat},{dest_lng}"
        
        # Request with current traffic
        result = gmaps.distance_matrix(
            origins=[origin],
            destinations=[destination],
            mode="driving",
            departure_time="now",  # Current traffic
            traffic_model="best_guess"
        )
        
        # Parse response
        if result['status'] != 'OK':
            logger.warning(f"API returned status: {result['status']}")
            return None
        
        element = result['rows'][0]['elements'][0]
        
        if element['status'] != 'OK':
            logger.warning(f"Element status: {element['status']}")
            return None
        
        # Extract data
        distance = element['distance']
        duration = element['duration']
        duration_in_traffic = element.get('duration_in_traffic', duration)
        
        # Calculate metrics
        distance_miles = distance['value'] / 1609.34  # meters to miles
        travel_time_seconds = duration_in_traffic['value']
        typical_time_seconds = duration['value']
        delay_seconds = travel_time_seconds - typical_time_seconds
        delay_minutes = round(delay_seconds / 60, 1)
        
        # Calculate speeds
        if travel_time_seconds > 0:
            avg_speed_mph = (distance_miles / travel_time_seconds) * 3600
        else:
            avg_speed_mph = None
        
        if typical_time_seconds > 0:
            typical_speed_mph = (distance_miles / typical_time_seconds) * 3600
        else:
            typical_speed_mph = None
        
        # Determine traffic level
        if delay_minutes <= 0:
            traffic_level = 'light'
        elif delay_minutes <= 2:
            traffic_level = 'moderate'
        elif delay_minutes <= 5:
            traffic_level = 'heavy'
        else:
            traffic_level = 'severe'
        
        measurement = {
            'measurement_time': datetime.now(),
            'origin_lat': origin_lat,
            'origin_lng': origin_lng,
            'destination_lat': dest_lat,
            'destination_lng': dest_lng,
            'distance_miles': round(distance_miles, 2),
            'travel_time_seconds': travel_time_seconds,
            'typical_time_seconds': typical_time_seconds,
            'delay_minutes': delay_minutes,
            'avg_speed_mph': round(avg_speed_mph, 2) if avg_speed_mph else None,
            'typical_speed_mph': round(typical_speed_mph, 2) if typical_speed_mph else None,
            'traffic_level': traffic_level,
            'data_source': 'google_maps',
            'raw_response': json.dumps(result)
        }
        
        logger.info(f"✓ Traffic: {traffic_level}, delay: {delay_minutes} min")
        
        return measurement
        
    except Exception as e:
        logger.error(f"Error measuring traffic: {e}")
        return None


def generate_points_around_location(center_lat: float, center_lng: float,
                                    radius_miles: float, 
                                    num_points: int = 4) -> List[Dict]:
    """
    Generate points in a circle around a location.
    
    Args:
        center_lat: Center latitude
        center_lng: Center longitude
        radius_miles: Radius in miles
        num_points: Number of points to generate
        
    Returns:
        List of coordinate dictionaries
    """
    import math
    
    points = []
    
    # Convert radius to degrees (approximate)
    # 1 degree latitude ≈ 69 miles
    radius_deg = radius_miles / 69.0
    
    for i in range(num_points):
        # Calculate angle (evenly spaced around circle)
        angle = (2 * math.pi * i) / num_points
        
        # Calculate offset
        lat_offset = radius_deg * math.cos(angle)
        lng_offset = radius_deg * math.sin(angle) / math.cos(math.radians(center_lat))
        
        # Create point
        point = {
            'lat': center_lat + lat_offset,
            'lng': center_lng + lng_offset,
            'direction': get_direction_name(i, num_points)
        }
        
        points.append(point)
    
    return points


def get_direction_name(index: int, total: int) -> str:
    """
    Get compass direction name for a point.
    
    Args:
        index: Point index (0-based)
        total: Total number of points
        
    Returns:
        Direction name (N, NE, E, SE, S, SW, W, NW)
    """
    if total == 4:
        directions = ['North', 'East', 'South', 'West']
    elif total == 8:
        directions = ['North', 'NE', 'East', 'SE', 'South', 'SW', 'West', 'NW']
    else:
        directions = [f"Point_{i}" for i in range(total)]
    
    return directions[index % len(directions)]


def collect_traffic_for_venue_id(venue_id: int, venue_name: str,
                                 venue_lat: float, venue_lng: float,
                                 radius_miles: float = 1.0) -> List[Dict]:
    """
    Collect traffic data for a specific venue and prepare for database insertion.
    
    Args:
        venue_id: Database venue ID
        venue_name: Venue name (for logging)
        venue_lat: Venue latitude
        venue_lng: Venue longitude
        radius_miles: Search radius
        
    Returns:
        List of measurement dictionaries ready for database insertion
    """
    logger.info(f"Collecting traffic for: {venue_name}")
    
    measurements = collect_traffic_around_venue(
        venue_lat, venue_lng, radius_miles
    )
    
    # Add venue_id to each measurement
    for measurement in measurements:
        measurement['venue_id'] = venue_id
    
    logger.info(f"✓ Collected {len(measurements)} measurements for {venue_name}")
    
    return measurements


if __name__ == "__main__":
    """
    Test the traffic collector
    """
    print("=" * 70)
    print("Traffic Collector Test")
    print("=" * 70)
    print()
    
    # Test with Isotopes Park
    print("Test 1: Single Traffic Measurement")
    print("-" * 70)
    
    # Measure from north of Isotopes Park to the park
    measurement = measure_traffic(
        origin_lat=35.0881,   # ~1 mile north
        origin_lng=-106.6044,
        dest_lat=35.0781,     # Isotopes Park
        dest_lng=-106.6044
    )
    
    if measurement:
        print("✓ Traffic measurement successful!")
        print(f"  Distance: {measurement['distance_miles']} miles")
        print(f"  Travel time: {measurement['travel_time_seconds']} seconds")
        print(f"  Delay: {measurement['delay_minutes']} minutes")
        print(f"  Traffic level: {measurement['traffic_level']}")
        print(f"  Avg speed: {measurement['avg_speed_mph']} mph")
    else:
        print("✗ Traffic measurement failed")
    
    print()
    
    # Test 2: Generate sample points
    print("Test 2: Generate Sample Points Around Venue")
    print("-" * 70)
    
    points = generate_points_around_location(
        center_lat=35.0781,
        center_lng=-106.6044,
        radius_miles=1.0,
        num_points=4
    )
    
    print(f"✓ Generated {len(points)} sample points:")
    for point in points:
        print(f"  {point['direction']}: ({point['lat']:.4f}, {point['lng']:.4f})")
    
    print()
    
    # Test 3: Collect traffic around venue
    print("Test 3: Collect Traffic Around Venue")
    print("-" * 70)
    print("This will make 4 API calls...")
    print()
    
    measurements = collect_traffic_around_venue(
        venue_lat=35.0781,
        venue_lng=-106.6044,
        radius_miles=1.0,
        num_points=4
    )
    
    print()
    print(f"✓ Collected {len(measurements)} measurements")
    
    if measurements:
        print("\nTraffic Summary:")
        for i, m in enumerate(measurements, 1):
            direction = generate_points_around_location(35.0781, -106.6044, 1.0, 4)[i-1]['direction']
            print(f"  {direction}: {m['traffic_level']} ({m['delay_minutes']} min delay)")
    
    print()
    print("=" * 70)
    print("Traffic Collector Tests Complete!")
    print("=" * 70)
    print()
    print(f"API calls made: ~{len(measurements) + 1}")