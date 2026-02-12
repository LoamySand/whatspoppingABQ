"""
Geocode all existing event venues and populate venue_locations table.
Run this once to geocode all venues from events table.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection, insert_venue
from utils.geocoding import batch_geocode_venues
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("Geocode All Event Venues")
print("=" * 70)
print()

# Step 1: Get all unique venue names from events
print("Step 1: Getting unique venues from events table...")
print("-" * 70)

conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT venue_name 
            FROM events 
            WHERE venue_name IS NOT NULL 
              AND venue_name != ''
            ORDER BY venue_name
        """)
        
        venue_names = [row[0] for row in cur.fetchall()]
        
finally:
    conn.close()

print(f"✓ Found {len(venue_names)} unique venues")
print()

if not venue_names:
    print("No venues to geocode!")
    exit(0)

# Show venues
print("Venues to geocode:")
for i, name in enumerate(venue_names, 1):
    print(f"  {i}. {name}")
print()

# Step 2: Geocode all venues
print("Step 2: Geocoding venues...")
print("-" * 70)

geocode_results = batch_geocode_venues(venue_names, delay=0.2)

print()

# Step 3: Insert into venue_locations table
print("Step 3: Inserting venues into database...")
print("-" * 70)

success_count = 0
fail_count = 0

for venue_name, geocode_data in geocode_results.items():
    if geocode_data:
        try:
            venue_id = insert_venue(
                venue_name=venue_name,
                latitude=geocode_data['latitude'],
                longitude=geocode_data['longitude'],
                address=geocode_data['formatted_address'],
                place_id=geocode_data['place_id']
            )
            success_count += 1
            print(f"✓ Inserted: {venue_name} (ID: {venue_id})")
        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to insert {venue_name}: {e}")
    else:
        fail_count += 1
        print(f"✗ Skipped (no geocode data): {venue_name}")

print()

# Step 4: Link events to venues
print("Step 4: Linking events to venue_locations...")
print("-" * 70)

conn = get_connection()
try:
    with conn.cursor() as cur:
        # Update events with venue_id
        cur.execute("""
            UPDATE events e
            SET venue_id = v.venue_id
            FROM venue_locations v
            WHERE e.venue_name = v.venue_name
              AND e.venue_id IS NULL
        """)
        
        updated = cur.rowcount
        conn.commit()
        
        print(f"✓ Linked {updated} events to venues")
        
finally:
    conn.close()

print()

# Step 5: Summary
print("=" * 70)
print("Geocoding Summary")
print("=" * 70)
print(f"Total venues processed: {len(venue_names)}")
print(f"Successfully geocoded: {success_count}")
print(f"Failed: {fail_count}")
print()

# Show sample
conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT venue_name, latitude, longitude, address
            FROM venue_locations
            LIMIT 5
        """)
        
        print("Sample venues in database:")
        for row in cur.fetchall():
            print(f"  - {row[0]}")
            print(f"    Coords: ({row[1]}, {row[2]})")
            print(f"    Address: {row[3]}")
finally:
    conn.close()

print()
print("=" * 70)
print("Geocoding Complete!")
print("=" * 70)