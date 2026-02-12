"""
Geocode a single venue and add to database.
Useful for adding new venues manually.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from utils.geocoding import geocode_venue
from database.db_utils import insert_venue

def main():
    venue_name = input("Enter venue name: ")
    
    print(f"\nGeocoding: {venue_name}")
    print("-" * 50)
    
    result = geocode_venue(venue_name)
    
    if not result:
        print(" Geocoding failed!")
        return
    
    print(f"✓ Geocoded successfully!")
    print(f"  Address: {result['formatted_address']}")
    print(f"  Coordinates: ({result['latitude']}, {result['longitude']})")
    print()
    
    save = input("Save to database? (y/n): ").lower()
    
    if save == 'y':
        try:
            venue_id = insert_venue(
                venue_name=venue_name,
                latitude=result['latitude'],
                longitude=result['longitude'],
                address=result['formatted_address'],
                place_id=result['place_id']
            )
            print(f"✓ Saved to database (ID: {venue_id})")
        except Exception as e:
            print(f" Error saving: {e}")
    else:
        print("Not saved.")

if __name__ == "__main__":
    main()