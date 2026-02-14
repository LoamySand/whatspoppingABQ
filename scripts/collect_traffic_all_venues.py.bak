# scripts/collect_traffic_all_venues.py
"""
Collect traffic data for all venues in database.
Run this periodically to build historical traffic data.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_all_venues, insert_traffic_measurement
from collectors.traffic_collector import collect_traffic_for_venue_id
import logging
from time import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("Collect Traffic Data for All Venues")
print("=" * 70)
print()

# Get all venues
print("Step 1: Loading venues from database...")
print("-" * 70)

venues = get_all_venues()

print(f"✓ Found {len(venues)} venues")
print()

if not venues:
    print("No venues found!")
    exit(0)

# Collect traffic for each venue
print("Step 2: Collecting traffic data...")
print("-" * 70)
print(f"This will make ~{len(venues) * 4} API calls")
print("(4 measurements per venue)")
print()

proceed = input("Proceed? (y/n): ").lower()

if proceed != 'y':
    print("Cancelled.")
    exit(0)

print()

total_measurements = 0
failed_venues = 0

for i, venue in enumerate(venues, 1):
    print(f"\n[{i}/{len(venues)}] {venue['venue_name']}")
    print("-" * 50)
    
    try:
        # Collect traffic measurements
        measurements = collect_traffic_for_venue_id(
            venue_id=venue['venue_id'],
            venue_name=venue['venue_name'],
            venue_lat=float(venue['latitude']),
            venue_lng=float(venue['longitude']),
            radius_miles=1.0
        )
        
        # Insert into database
        for measurement in measurements:
            try:
                measurement_id = insert_traffic_measurement(
                    venue_id=venue['venue_id'],
                    measurement_time=measurement['measurement_time'],
                    traffic_data=measurement
                )
                total_measurements += 1
                
            except Exception as e:
                logger.error(f"Error inserting measurement: {e}")
        
        print(f"✓ Inserted {len(measurements)} measurements")
        
        # Rate limiting (avoid hitting API limits)
        if i < len(venues):
            sleep(1)  # 1 second between venues
        
    except Exception as e:
        logger.error(f"Error processing {venue['venue_name']}: {e}")
        failed_venues += 1

print()
print("=" * 70)
print("Traffic Collection Summary")
print("=" * 70)
print(f"Venues processed: {len(venues)}")
print(f"Total measurements: {total_measurements}")
print(f"Failed venues: {failed_venues}")
print()

# Show sample data
from database.db_utils import get_connection

conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                v.venue_name,
                COUNT(tm.measurement_id) as count,
                AVG(tm.delay_minutes) as avg_delay,
                MAX(tm.measurement_time) as last_measured
            FROM venue_locations v
            LEFT JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
            GROUP BY v.venue_id, v.venue_name
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("Top venues by measurement count:")
        for row in cur.fetchall():
            venue_name, count, avg_delay, last_measured = row
            if count > 0:
                print(f"  {venue_name}: {count} measurements, avg delay: {avg_delay:.1f} min")
finally:
    conn.close()

print()
print("=" * 70)
print("Traffic Collection Complete! ✅")
print("=" * 70)