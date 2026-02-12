# utils/geocoding.py
"""
Geocoding utilities for converting venue names to coordinates.
Uses Google Maps Geocoding API.
"""

import os
from dotenv import load_dotenv
import googlemaps
import logging
from typing import Optional, Dict, Tuple
from time import sleep

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


def geocode_venue(venue_name: str, city: str = "Albuquerque", 
                  state: str = "NM") -> Optional[Dict]:
    """
    Geocode a venue name to get coordinates and formatted address.
    
    Args:
        venue_name: Name of the venue
        city: City name (default: Albuquerque)
        state: State code (default: NM)
        
    Returns:
        Dictionary with geocoding results or None if failed
        {
            'latitude': float,
            'longitude': float,
            'formatted_address': str,
            'place_id': str
        }
    """
    if not gmaps:
        logger.error("Google Maps client not initialized")
        return None
    
    # Build search query
    query = f"{venue_name}, {city}, {state}"
    
    try:
        logger.info(f"Geocoding: {query}")
        
        # Call Geocoding API
        geocode_result = gmaps.geocode(query)
        
        if not geocode_result:
            logger.warning(f"No results found for: {query}")
            return None
        
        # Get first (best) result
        result = geocode_result[0]
        location = result['geometry']['location']
        
        geocode_data = {
            'latitude': location['lat'],
            'longitude': location['lng'],
            'formatted_address': result['formatted_address'],
            'place_id': result['place_id']
        }
        
        logger.info(f"✓ Geocoded: {venue_name} → ({location['lat']}, {location['lng']})")
        
        return geocode_data
        
    except Exception as e:
        logger.error(f"Error geocoding {venue_name}: {e}")
        return None


def reverse_geocode(latitude: float, longitude: float) -> Optional[Dict]:
    """
    Reverse geocode coordinates to get address.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Dictionary with address info or None
    """
    if not gmaps:
        logger.error("Google Maps client not initialized")
        return None
    
    try:
        logger.info(f"Reverse geocoding: ({latitude}, {longitude})")
        
        result = gmaps.reverse_geocode((latitude, longitude))
        
        if not result:
            logger.warning(f"No results found for coordinates: ({latitude}, {longitude})")
            return None
        
        address_data = {
            'formatted_address': result[0]['formatted_address'],
            'place_id': result[0]['place_id']
        }
        
        return address_data
        
    except Exception as e:
        logger.error(f"Error reverse geocoding: {e}")
        return None


def batch_geocode_venues(venue_names: list, delay: float = 0.1) -> Dict[str, Dict]:
    """
    Geocode multiple venues with rate limiting.
    
    Args:
        venue_names: List of venue names to geocode
        delay: Delay between requests (seconds) to avoid rate limits
        
    Returns:
        Dictionary mapping venue_name to geocode results
        {
            'Venue Name': {latitude, longitude, address, place_id},
            ...
        }
    """
    results = {}
    
    logger.info(f"Batch geocoding {len(venue_names)} venues...")
    
    for i, venue_name in enumerate(venue_names, 1):
        logger.info(f"Processing {i}/{len(venue_names)}: {venue_name}")
        
        geocode_data = geocode_venue(venue_name)
        
        if geocode_data:
            results[venue_name] = geocode_data
        else:
            results[venue_name] = None
            logger.warning(f"Failed to geocode: {venue_name}")
        
        # Rate limiting
        if i < len(venue_names):
            sleep(delay)
    
    success_count = sum(1 for v in results.values() if v is not None)
    logger.info(f"Batch geocoding complete: {success_count}/{len(venue_names)} successful")
    
    return results


def get_distance_between_points(lat1: float, lng1: float, 
                                lat2: float, lng2: float) -> Optional[float]:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1, lng1: First point coordinates
        lat2, lng2: Second point coordinates
        
    Returns:
        Distance in miles or None if calculation fails
    """
    from math import radians, sin, cos, sqrt, atan2
    
    try:
        # Radius of Earth in miles
        R = 3959.0
        
        # Convert to radians
        lat1_rad = radians(lat1)
        lng1_rad = radians(lng1)
        lat2_rad = radians(lat2)
        lng2_rad = radians(lng2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        
        return round(distance, 2)
        
    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        return None


if __name__ == "__main__":
    """
    Test the geocoding module
    """
    print("=" * 70)
    print("Geocoding Module Test")
    print("=" * 70)
    print()
    
    # Test 1: Single venue geocoding
    print("Test 1: Single Venue Geocoding")
    print("-" * 70)
    
    test_venues = [
        "Isotopes Park",
        'University Arena ("the Pit")',
        "Tingley Coliseum",
        "Old Town Albuquerque"
    ]
    
    for venue in test_venues:
        result = geocode_venue(venue)
        if result:
            print(f"✓ {venue}")
            print(f"  Address: {result['formatted_address']}")
            print(f"  Coordinates: ({result['latitude']}, {result['longitude']})")
        else:
            print(f"✗ Failed: {venue}")
        print()
    
    # Test 2: Reverse geocoding
    print("Test 2: Reverse Geocoding")
    print("-" * 70)
    
    result = reverse_geocode(35.0781471, -106.6044161)
    if result:
        print(f"✓ Reverse geocoding successful")
        print(f"  Address: {result['formatted_address']}")
    print()
    
    # Test 3: Distance calculation
    print("Test 3: Distance Calculation")
    print("-" * 70)
    
    # Distance from Isotopes Park to The Pit
    distance = get_distance_between_points(
        35.0781471, -106.6044161,  # Isotopes Park
        35.0833, -106.6197           # The Pit
    )
    print(f"✓ Distance: Isotopes Park to The Pit = {distance} miles")
    print()
    
    # Test 4: Batch geocoding
    print("Test 4: Batch Geocoding")
    print("-" * 70)
    
    batch_results = batch_geocode_venues(test_venues, delay=0.2)
    print(f"\n✓ Batch geocoding complete")
    print(f"  Successful: {sum(1 for v in batch_results.values() if v)}/{len(batch_results)}")
    
    print()
    print("=" * 70)
    print("Geocoding Module Tests Complete!")
    print("=" * 70)