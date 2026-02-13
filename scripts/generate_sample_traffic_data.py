"""
Generate comprehensive sample traffic data for testing correlation analysis.
Creates realistic before/during/after traffic patterns for multiple events.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection, insert_traffic_measurement
from datetime import datetime, timedelta
import random
import json

print("=" * 70)
print("Generate Sample Traffic Data")
print("=" * 70)
print()

# Get events with times from the past week
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
            WHERE e.event_start_time IS NOT NULL
              AND e.event_start_date >= CURRENT_DATE - 7
            ORDER BY e.event_start_date DESC
            LIMIT 15
        """)
        
        events = []
        for row in cur.fetchall():
            events.append({
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
            })

finally:
    conn.close()

if not events:
    print("No events found! Run event scraping first.")
    exit(1)

print(f"Found {len(events)} events to generate traffic data for")
print()

# Define traffic patterns by category
TRAFFIC_PATTERNS = {
    'Sports': {
        'before_delay': (-0.5, 1.0),
        'during_delay': (2.0, 5.0),
        'after_delay': (3.0, 7.0),
        'before_speed': (28, 35),
        'during_speed': (18, 25),
        'after_speed': (15, 22),
        'impact_level': 'high'
    },
    'Sports/Fitness': {
        'before_delay': (-0.5, 1.0),
        'during_delay': (2.0, 5.0),
        'after_delay': (3.0, 7.0),
        'before_speed': (28, 35),
        'during_speed': (18, 25),
        'after_speed': (15, 22),
        'impact_level': 'high'
    },
    'Music': {
        'before_delay': (-0.3, 0.8),
        'during_delay': (1.5, 4.0),
        'after_delay': (2.0, 5.0),
        'before_speed': (25, 32),
        'during_speed': (20, 27),
        'after_speed': (18, 25),
        'impact_level': 'moderate'
    },
    'Festival': {
        'before_delay': (-0.2, 1.5),
        'during_delay': (3.0, 8.0),
        'after_delay': (4.0, 10.0),
        'before_speed': (22, 30),
        'during_speed': (15, 22),
        'after_speed': (12, 20),
        'impact_level': 'severe'
    },
    'Festivals & Special Events': {
        'before_delay': (-0.2, 1.5),
        'during_delay': (3.0, 8.0),
        'after_delay': (4.0, 10.0),
        'before_speed': (22, 30),
        'during_speed': (15, 22),
        'after_speed': (12, 20),
        'impact_level': 'severe'
    },
    'Theatre': {
        'before_delay': (-0.5, 0.5),
        'during_delay': (0.5, 2.0),
        'after_delay': (1.0, 3.0),
        'before_speed': (28, 35),
        'during_speed': (25, 32),
        'after_speed': (22, 30),
        'impact_level': 'low'
    },
    'Arts & Culture': {
        'before_delay': (-0.5, 0.5),
        'during_delay': (0.5, 1.5),
        'after_delay': (0.8, 2.5),
        'before_speed': (28, 35),
        'during_speed': (25, 32),
        'after_speed': (23, 30),
        'impact_level': 'low'
    },
    'Food, Wine & Beer': {
        'before_delay': (-0.3, 0.8),
        'during_delay': (0.8, 2.5),
        'after_delay': (1.0, 3.0),
        'before_speed': (26, 33),
        'during_speed': (23, 30),
        'after_speed': (20, 28),
        'impact_level': 'moderate'
    },
    'General': {
        'before_delay': (-0.5, 0.5),
        'during_delay': (0.5, 2.0),
        'after_delay': (0.8, 2.5),
        'before_speed': (28, 35),
        'during_speed': (24, 31),
        'after_speed': (22, 29),
        'impact_level': 'low'
    }
}

def get_pattern(category):
    """Get traffic pattern for category or default"""
    for key in TRAFFIC_PATTERNS.keys():
        if key in category:
            return TRAFFIC_PATTERNS[key]
    return TRAFFIC_PATTERNS['General']

def create_measurement(venue, event_datetime, offset_hours, pattern_key, pattern):
    """Create a single traffic measurement"""
    measurement_time = event_datetime + timedelta(hours=offset_hours)
    
    # Get delay range for this time period
    delay_range = pattern[f'{pattern_key}_delay']
    speed_range = pattern[f'{pattern_key}_speed']
    
    delay = random.uniform(*delay_range)
    speed = random.uniform(*speed_range)
    
    # Determine traffic level
    if delay < 0.5:
        traffic_level = 'light'
    elif delay < 2:
        traffic_level = 'moderate'
    elif delay < 5:
        traffic_level = 'heavy'
    else:
        traffic_level = 'severe'
    
    traffic_data = {
        'traffic_level': traffic_level,
        'avg_speed_mph': round(speed, 2),
        'typical_speed_mph': 30.0,
        'travel_time_seconds': int(120 / speed * 30),  # time = distance/speed
        'typical_time_seconds': 240,
        'delay_minutes': round(delay, 2),
        'data_source': 'sample_data',
        'origin_lat': venue['latitude'] + random.uniform(-0.01, 0.01),
        'origin_lng': venue['longitude'] + random.uniform(-0.01, 0.01),
        'destination_lat': venue['latitude'],
        'destination_lng': venue['longitude'],
        'distance_miles': 1.0,
        'raw_response': json.dumps({'sample': True, 'pattern': pattern_key})
    }
    
    return measurement_time, traffic_data

# Generate traffic for each event
total_measurements = 0

for i, event in enumerate(events, 1):
    print(f"[{i}/{len(events)}] {event['event_name']}")
    print(f"  Category: {event['category']}")
    print(f"  Date/Time: {event['event_start_date']} at {event['event_start_time']}")
    
    event_datetime = datetime.combine(event['event_start_date'], event['event_start_time'])
    pattern = get_pattern(event['category'])
    
    print(f"  Pattern: {pattern['impact_level']} impact")
    
    event_measurements = 0
    
    # Before event (1 hour before, 2 measurements)
    for j in range(2):
        meas_time, traffic_data = create_measurement(
            event, event_datetime, -1.0, 'before', pattern
        )
        
        insert_traffic_measurement(
            venue_id=event['venue_id'],
            measurement_time=meas_time,
            traffic_data=traffic_data
        )
        event_measurements += 1
    
    # During/After event (1 hour after, 2 measurements)
    # We use "after" pattern since it's post-event start
    for j in range(2):
        meas_time, traffic_data = create_measurement(
            event, event_datetime, 1.0, 'after', pattern
        )
        
        insert_traffic_measurement(
            venue_id=event['venue_id'],
            measurement_time=meas_time,
            traffic_data=traffic_data
        )
        event_measurements += 1
    
    total_measurements += event_measurements
    print(f"  ✓ Created {event_measurements} measurements")
    print()

print("=" * 70)
print("Sample Data Generation Complete!")
print("=" * 70)
print(f"Total measurements created: {total_measurements}")
print(f"Events with data: {len(events)}")
print()

print("Summary by expected impact:")
print("-" * 70)

impact_counts = {}
for event in events:
    pattern = get_pattern(event['category'])
    level = pattern['impact_level']
    impact_counts[level] = impact_counts.get(level, 0) + 1

for level in ['severe', 'high', 'moderate', 'low']:
    count = impact_counts.get(level, 0)
    if count > 0:
        print(f"  {level.capitalize()}: {count} events")

print()
print("Next steps:")
print("  1. Run correlation analysis:")
print("     python analysis\\event_traffic_correlation.py")
print()
print("  2. Generate report:")
print("     python scripts\\generate_traffic_report.py")
print()
print("=" * 70)