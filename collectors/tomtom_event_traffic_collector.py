"""
Event traffic collection using TomTom Flow API at venue location
Simplified to single point measurement for accuracy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_utils import get_connection, insert_traffic_measurement
from collectors.tomtom_flow_collector import measure_traffic_tomtom
from datetime import datetime, timedelta
import logging
from time import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_events_needing_collection(window_minutes: int = 30) -> list:
    """
    Get events that need traffic collection in the next N minutes.
    """
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
                    v.venue_id,
                    v.venue_name,
                    v.latitude,
                    v.longitude
                FROM events e
                JOIN venue_locations v ON e.venue_id = v.venue_id
                WHERE e.event_start_date = CURRENT_DATE
                  AND e.event_start_time IS NOT NULL
                  AND e.event_start_time BETWEEN 
                      CURRENT_TIME - INTERVAL '2 hours' AND 
                      CURRENT_TIME + INTERVAL '2 hours %s minutes'
                ORDER BY e.event_start_time
            """ % window_minutes)
            
            events = []
            for row in cur.fetchall():
                events.append({
                    'event_id': row[0],
                    'event_name': row[1],
                    'event_start_date': row[2],
                    'event_start_time': row[3],
                    'category': row[4],
                    'venue_id': row[5],
                    'venue_name': row[6],
                    'latitude': float(row[7]),
                    'longitude': float(row[8])
                })
            
            return events
    finally:
        conn.close()


def should_collect_now_tomtom(event: dict) -> dict:
    """
    Determine if we should collect traffic now for this event.
    Collects every 30 minutes from 2hr before to 2hr after.
    """
    now = datetime.now()
    
    event_datetime = datetime.combine(
        event['event_start_date'],
        event['event_start_time']
    )
    
    time_diff_minutes = (event_datetime - now).total_seconds() / 60
    
    # Collection points: -120, -90, -60, -30, 0, +30, +60, +90, +120 minutes
    collection_points = [-120, -90, -60, -30, 0, 30, 60, 90, 120]
    
    for target_minutes in collection_points:
        if abs(time_diff_minutes - target_minutes) <= 15:
            
            if target_minutes < -15:
                window = 'before'
            elif target_minutes > 15:
                window = 'after'
            else:
                window = 'during'
            
            return {
                'collect': True,
                'window': window,
                'collection_point': target_minutes,
                'event_time': event_datetime,
                'reason': f"Collection point at {target_minutes} min from event ({window})"
            }
    
    return {
        'collect': False,
        'reason': f"Not at a collection point (event in {time_diff_minutes:.0f} min)"
    }


def collect_traffic_for_event_tomtom(event: dict) -> int:
    """
    Collect traffic measurement for an event at the venue location.
    
    Single point measurement for simplicity and accuracy.
    """
    logger.info(f"Collecting traffic (TomTom Flow) for: {event['event_name']}")
    logger.info(f"  Event ID: {event['event_id']}")
    logger.info(f"  Location: {event['venue_name']}")
    
    # Measure traffic at venue location
    measurement = measure_traffic_tomtom(
        origin_lat=event['latitude'],
        origin_lng=event['longitude'],
        dest_lat=event['latitude'],
        dest_lng=event['longitude'],
        point_name=event['event_name']
    )
    
    if measurement:
        # Add event context
        measurement['venue_id'] = event['venue_id']
        measurement['is_baseline'] = False
        
        try:
            insert_traffic_measurement(
                venue_id=event['venue_id'],
                measurement_time=measurement['measurement_time'],
                traffic_data=measurement,
                event_id=event['event_id']
            )
            
            logger.info(f" Collected 1 measurement")
            return 1
            
        except Exception as e:
            logger.error(f"Error inserting measurement: {e}")
            return 0
    
    return 0


def run_tomtom_event_collection(max_calls: int = 50):
    """
    Main function for TomTom event traffic collection.
    """
    from datetime import datetime
    logger.info("=" * 70)
    logger.info(f"CALLED: run_tomtom_event_collection at {datetime.now()}")
    logger.info(f"Max calls allowed: {max_calls}")
    logger.info("=" * 70)
    
    # ... rest of function
    
    events = get_events_needing_collection(window_minutes=30)
    
    logger.info(f"Found {len(events)} events in collection window")
    
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
        decision = should_collect_now_tomtom(event)
        
        logger.info(f"\nEvent: {event['event_name']}")
        logger.info(f"  Start time: {event['event_start_time']}")
        logger.info(f"  Decision: {decision['reason']}")
        
        if not decision['collect']:
            continue
        
        logger.info(f"  Collection point: {decision['collection_point']} min")
        logger.info(f"  Window: {decision['window']}")
        
        if api_calls_made >= max_calls:
            logger.warning(f"Reached max API calls ({max_calls}), stopping")
            break
        
        measurements = collect_traffic_for_event_tomtom(event)
        
        total_measurements += measurements
        api_calls_made += measurements
        events_collected += 1
        
        sleep(0.2)  # Rate limiting
    
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
    Test TomTom event collection
    """
    print("=" * 70)
    print("TomTom Event Traffic Collector Test (Single Point)")
    print("=" * 70)
    print()
    
    stats = run_tomtom_event_collection(max_calls=20)
    
    print()
    print("Test complete!")
    print(f"API calls made: {stats['api_calls_made']}")