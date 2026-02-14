# scripts/collect_traffic_for_event.py
"""
Manually collect traffic for a specific event (for testing).
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
from collectors.event_traffic_collector import collect_traffic_for_event
from collectors.traffic_collection_rules import get_collection_plan
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("Manual Traffic Collection for Event")
print("=" * 70)
print()

# Get upcoming events
conn = get_connection()

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                e.event_id,
                e.event_name,
                e.event_start_date,
                e.event_start_time,
                e.category,
                e.is_multi_day,
                v.venue_id,
                v.venue_name,
                v.latitude,
                v.longitude
            FROM events e
            JOIN venue_locations v ON e.venue_id = v.venue_id
            WHERE e.event_start_date >= CURRENT_DATE
              AND e.event_start_time IS NOT NULL
            ORDER BY e.event_start_date, e.event_start_time
            LIMIT 20
        """)
        
        events = []
        for i, row in enumerate(cur.fetchall(), 1):
            event = {
                'event_id': row[0],
                'event_name': row[1],
                'event_start_date': row[2],
                'event_start_time': row[3],
                'category': row[4],
                'is_multi_day': row[5],
                'venue_id': row[6],
                'venue_name': row[7],
                'latitude': float(row[8]),
                'longitude': float(row[9])
            }
            events.append(event)
            
            # Display
            print(f"{i}. {event['event_name']}")
            print(f"   {event['event_start_date']} at {event['event_start_time']}")
            print(f"   {event['venue_name']} - {event['category']}")
            print()
finally:
    conn.close()

if not events:
    print("No upcoming events with times found!")
    exit(0)

# Select event
choice = input("Select event number (or 'q' to quit): ")

if choice.lower() == 'q':
    print("Cancelled.")
    exit(0)

try:
    event_idx = int(choice) - 1
    if event_idx < 0 or event_idx >= len(events):
        print("Invalid selection!")
        exit(1)
    
    event = events[event_idx]
except ValueError:
    print("Invalid input!")
    exit(1)

print()
print(f"Selected: {event['event_name']}")
print("-" * 70)

# Get collection plan
plan = get_collection_plan(event)

print(f"Collection plan: {plan['type']}")
print(f"  Collect before: {plan['collect_before']}")
print(f"  Collect after: {plan.get('collect_after', False)}")
print(f"  Directions: {plan['num_directions']} ({', '.join(plan['directions'])})")
print(f"  Estimated API calls: {plan['estimated_calls']}")
print()

proceed = input("Proceed with collection? (y/n): ").lower()

if proceed != 'y':
    print("Cancelled.")
    exit(0)

print()
print("Collecting traffic...")
print("-" * 70)

measurements = collect_traffic_for_event(event, plan)

print()
print(f"✓ Collected {measurements} traffic measurements")
print()
print("Check database:")
print(f"  SELECT * FROM traffic_measurements WHERE venue_id = {event['venue_id']} ORDER BY measurement_time DESC LIMIT 5;")