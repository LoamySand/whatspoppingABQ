"""
Smart traffic collector for events based on collection rules.
Collects traffic before/after events based on event type and timing.
"""

import sys
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')

from dotenv import load_dotenv
load_dotenv(env_path)

from database.db_utils import get_connection, insert_traffic_measurement
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection, insert_traffic_measurement
from collectors.traffic_collector import measure_traffic, generate_points_around_location
from collectors.traffic_collection_rules import get_collection_plan
from datetime import datetime, timedelta
import logging
from time import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_events_needing_collection(window_hours: int = 2) -> list:
    """
    Get events that need traffic collection in the next N hours.
    
    Args:
        window_hours: Look ahead window (default 2 hours)
        
    Returns:
        List of event dictionaries with venue info
    """
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            # Get events happening soon with venue coordinates
            cur.execute("""
                SELECT 
                    e.event_id,
                    e.event_name,
                    e.event_start_date,
                    e.event_start_time,
                    e.event_end_date,
                    e.is_multi_day,
                    e.category,
                    v.venue_id,
                    v.venue_name,
                    v.latitude,
                    v.longitude
                FROM events e
                JOIN venue_locations v ON e.venue_id = v.venue_id
                WHERE e.event_start_date = CURRENT_DATE
                  AND e.event_start_time IS NOT NULL
                  AND e.event_start_time BETWEEN 
                      CURRENT_TIME AND 
                      CURRENT_TIME + INTERVAL '%s hours'
                ORDER BY e.event_start_time
            """ % window_hours)
            
            events = []
            for row in cur.fetchall():
                events.append({
                    'event_id': row[0],
                    'event_name': row[1],
                    'event_start_date': row[2],
                    'event_start_time': row[3],
                    'event_end_date': row[4],
                    'is_multi_day': row[5],
                    'category': row[6],
                    'venue_id': row[7],
                    'venue_name': row[8],
                    'latitude': float(row[9]),
                    'longitude': float(row[10])
                })
            
            return events
    finally:
        conn.close()

def should_collect_now(event: dict, collection_plan: dict) -> dict:
    """
    Determine if we should collect traffic now for this event.
    
    Args:
        event: Event dictionary
        collection_plan: Collection plan from get_collection_plan()
        
    Returns:
        Dictionary with collection decision and type
    """
    if not collection_plan.get('collect'):
        return {'collect': False, 'reason': 'Event skipped by plan'}
    
    # Get current time
    now = datetime.now()
    
    # Calculate event datetime
    event_datetime = datetime.combine(
        event['event_start_date'],
        event['event_start_time']
    )
    
    # Calculate time difference in hours
    time_until_event = (event_datetime - now).total_seconds() / 3600  # hours
    
    # Calculate collection windows
    # Before: collect when 0.5 to 1.5 hours before event
    # After: collect when 0.5 to 1.5 hours after event
    
    # Check if we're in the "before" window (30 min to 90 min before event)
    if collection_plan['collect_before']:
        hours_before = collection_plan['hours_before']
        
        # Window: 30 min before target time to 30 min after target time
        # Target time is "hours_before" before the event
        # So if event is at 16:19 and we want to collect 1hr before (15:19)
        # Window is 14:49 to 15:49
        
        if 0.5 <= time_until_event <= 1.5:  # 30-90 min before event
            return {
                'collect': True,
                'window': 'before',
                'event_time': event_datetime,
                'time_until_event': time_until_event,
                'reason': f"In before-event window ({time_until_event*60:.0f} min before event at {event_datetime.strftime('%H:%M')})"
            }
    
    # Check if we're in the "after" window (30-90 min after event)
    if collection_plan.get('collect_after'):
        # time_until_event will be negative after the event
        if -1.5 <= time_until_event <= -0.5:  # 30-90 min after event
            return {
                'collect': True,
                'window': 'after',
                'event_time': event_datetime,
                'time_until_event': time_until_event,
                'reason': f"In after-event window ({abs(time_until_event)*60:.0f} min after event at {event_datetime.strftime('%H:%M')})"
            }
    
    return {
        'collect': False,
        'reason': f"Outside collection windows ({time_until_event*60:.0f} min from event at {event_datetime.strftime('%H:%M')})"
    }


def collect_traffic_for_event(event: dict, collection_plan: dict) -> int:
    """
    Collect traffic measurements for an event based on plan.
    
    Args:
        event: Event dictionary with venue info
        collection_plan: Collection plan dictionary
        
    Returns:
        Number of measurements collected
    """
    logger.info(f"Collecting traffic for: {event['event_name']}")
    logger.info(f"  Category: {event['category']}")
    logger.info(f"  Type: {collection_plan['type']}")
    logger.info(f"  Directions: {collection_plan['num_directions']}")
    
    # Generate sample points
    all_points = generate_points_around_location(
        event['latitude'],
        event['longitude'],
        radius_miles=1.0,
        num_points=4
    )
    
    # Filter to selected directions
    selected_points = [
        p for p in all_points 
        if p['direction'] in collection_plan['directions']
    ]
    
    logger.info(f"  Sampling {len(selected_points)} directions: {', '.join([p['direction'] for p in selected_points])}")
    
    measurements_collected = 0
    
    for point in selected_points:
        # Measure traffic
        measurement = measure_traffic(
            origin_lat=point['lat'],
            origin_lng=point['lng'],
            dest_lat=event['latitude'],
            dest_lng=event['longitude']
        )
        
        if measurement:
            # Add event context
            measurement['venue_id'] = event['venue_id']
            
            # Insert to database
            try:
                insert_traffic_measurement(
                    venue_id=event['venue_id'],
                    measurement_time=measurement['measurement_time'],
                    traffic_data=measurement
                )
                measurements_collected += 1
            except Exception as e:
                logger.error(f"Error inserting measurement: {e}")
        
        # Rate limiting
        sleep(0.5)
    
    logger.info(f"✓ Collected {measurements_collected} measurements for {event['event_name']}")
    
    return measurements_collected


def run_scheduled_collection(max_calls: int = 50):
    """
    Main function to run scheduled traffic collection.
    Checks for upcoming events and collects traffic based on rules.
    
    Args:
        max_calls: Maximum API calls to make in this run
        
    Returns:
        Dictionary with collection statistics
    """
    logger.info("=" * 70)
    logger.info("Starting Scheduled Traffic Collection")
    logger.info("=" * 70)
    
    # Get events in next 2 hours
    events = get_events_needing_collection(window_hours=2)
    
    logger.info(f"Found {len(events)} events in next 2 hours")
    
    if not events:
        logger.info("No events need collection at this time")
        return {
            'events_checked': 0,
            'events_collected': 0,
            'measurements_collected': 0,
            'api_calls_made': 0
        }
    
    total_measurements = 0
    events_collected = 0
    api_calls_made = 0
    
    for event in events:
        # Get collection plan
        collection_plan = get_collection_plan(event)
        
        # Check if we should collect now
        decision = should_collect_now(event, collection_plan)
        
        logger.info(f"\nEvent: {event['event_name']}")
        logger.info(f"  Start time: {event['event_start_time']}")
        logger.info(f"  Decision: {decision['reason']}")
        
        if not decision['collect']:
            continue
        
        logger.info(f"  Collection window: {decision['window']}")
        
        # Check if we've hit the call limit
        if api_calls_made >= max_calls:
            logger.warning(f"Reached max API calls ({max_calls}), stopping")
            break
        
        # Collect traffic
        measurements = collect_traffic_for_event(event, collection_plan)
        
        total_measurements += measurements
        api_calls_made += measurements
        events_collected += 1
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("Collection Summary")
    logger.info("=" * 70)
    logger.info(f"Events checked: {len(events)}")
    logger.info(f"Events collected: {events_collected}")
    logger.info(f"Measurements: {total_measurements}")
    logger.info(f"API calls: {api_calls_made}")
    logger.info("=" * 70)
    
    return {
        'events_checked': len(events),
        'events_collected': events_collected,
        'measurements_collected': total_measurements,
        'api_calls_made': api_calls_made
    }


if __name__ == "__main__":
    """
    Test the event traffic collector
    """
    print("=" * 70)
    print("Event Traffic Collector - Test Run")
    print("=" * 70)
    print()
    
    stats = run_scheduled_collection(max_calls=20)
    
    print()
    print("Test complete!")
    print(f"API calls made: {stats['api_calls_made']}")