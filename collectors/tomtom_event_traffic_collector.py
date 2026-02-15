# collectors/tomtom_event_collector.py
"""
Event traffic collection using TomTom Routing API
Uses route-based measurements (comparable to Google Maps)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_utils import get_connection, insert_traffic_measurement
from collectors.tomtom_routing_collector import measure_traffic_tomtom
from collectors.traffic_collector import generate_points_around_location
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


def collect_traffic_for_event_tomtom(event: dict, num_directions: int = 2) -> int:
    """
    Collect traffic measurements for an event using TomTom Routing API.
    """
    logger.info(f"Collecting traffic (TomTom Routing) for: {event['event_name']}")
    logger.info(f"  Event ID: {event['event_id']}")
    
    # Generate sample points
    all_points = generate_points_around_location(
        event['latitude'],
        event['longitude'],
        radius_miles=1.0,
        num_points=4
    )
    
    # Use North and South directions
    selected_points = [p for p in all_points if p['direction'] in ['North', 'South']][:num_directions]
    
    logger.info(f"  Sampling {len(selected_points)} directions")
    
    measurements_collected = 0
    
    for point in selected_points:
        # Use TomTom Routing API (route from point to venue)
        measurement = measure_traffic_tomtom(
            origin_lat=point['lat'],
            origin_lng=point['lng'],
            dest_lat=event['latitude'],
            dest_lng=event['longitude'],
            point_name=f"{event['event_name']} - {point['direction']}"
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
                measurements_collected += 1
            except Exception as e:
                logger.error(f"Error inserting measurement: {e}")
        
        sleep(0.2)  # Rate limiting
    
    logger.info(f" Collected {measurements_collected} measurements")
    
    return measurements_collected


def run_tomtom_event_collection(max_calls: int = 50):
    """
    Main function for TomTom event traffic collection.
    """
    logger.info("=" * 70)
    logger.info("TomTom Event Traffic Collection (Routing API)")
    logger.info("=" * 70)
    
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
        
        measurements = collect_traffic_for_event_tomtom(event, num_directions=2)
        
        total_measurements += measurements
        api_calls_made += measurements
        events_collected += 1
    
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
    print("TomTom Event Traffic Collector Test (Routing API)")
    print("=" * 70)
    print()
    
    stats = run_tomtom_event_collection(max_calls=20)
    
    print()
    print("Test complete!")
    print(f"API calls made: {stats['api_calls_made']}")