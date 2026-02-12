# scripts/create_test_event.py
"""
Create a test event starting in 2 hours for testing traffic collection.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import insert_events, insert_venue
from datetime import datetime, timedelta

print("=" * 70)
print("Create Test Event for Traffic Collection")
print("=" * 70)
print()

# Calculate event time (1 hours from now)
event_start = datetime.now() + timedelta(hours=1)
event_date = event_start.date()
event_time = event_start.time().replace(second=0, microsecond=0)

print(f"Test event will start at: {event_start.strftime('%Y-%m-%d %H:%M')}")
print()

# First, ensure venue exists
print("Creating test venue...")

venue_id = insert_venue(
    venue_name="Isotopes Park",
    latitude=35.0781471,
    longitude=-106.6044161,
    address="1601 Avenida Cesar Chavez SE, Albuquerque, NM 87106",
    place_id="ChIJN1t_tDeuEzcRUoH_D90hUEE"
)

print(f"✓ Venue created/updated (ID: {venue_id})")
print()

# Create test event
test_event = {
    'event_name': 'TEST EVENT - Traffic Collection Test',
    'venue_name': 'Isotopes Park',
    'event_start_date': str(event_date),
    'event_end_date': str(event_date),
    'event_start_time': str(event_time),
    'event_end_time': str((datetime.combine(event_date, event_time) + timedelta(hours=2)).time()),
    'is_multi_day': False,
    'category': 'Sports',
    'sponsor': 'Test Sponsor',
    'cost_min': 0.0,
    'cost_max': 0.0,
    'cost_description': 'Free Test Event',
    'source_url': 'https://test.com/event',
    'venue_id': venue_id
}

print("Creating test event...")

inserted = insert_events([test_event])

print(f"✓ Test event created!")
print()

print("Event details:")
print("-" * 70)
print(f"Name: {test_event['event_name']}")
print(f"Venue: {test_event['venue_name']}")
print(f"Date: {test_event['event_start_date']}")
print(f"Time: {test_event['event_start_time']}")
print(f"Category: {test_event['category']}")
print()

print("Collection windows:")
before_time = event_start - timedelta(hours=1)
after_time = event_start + timedelta(hours=1)
print(f"  Before event: {before_time.strftime('%H:%M')} (±30 min)")
print(f"  After event: {after_time.strftime('%H:%M')} (±30 min)")
print()

print("=" * 70)
print("Test event created successfully!")
print("=" * 70)
print()
print("To test traffic collection:")
print(f"  1. Wait until ~{before_time.strftime('%H:%M')} (1 hour before event)")
print("  2. Run: python scripts\\auto_collect_traffic.py")
print("  3. Check traffic_measurements table for new data")
print()
print("To delete test event:")
print("  DELETE FROM events WHERE event_name LIKE 'TEST EVENT%';")