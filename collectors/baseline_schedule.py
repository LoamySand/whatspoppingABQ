"""
Baseline traffic collection scheduler.
Collects baseline traffic at 6 time points per day for assigned venue group.
Dynamically splits venues into 4 groups for 4-week rotation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_utils import get_connection, insert_traffic_measurement
from collectors.baseline_collector_tomtom import collect_baseline_for_venue_tomtom
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Baseline collection time slots
BASELINE_TIME_SLOTS = [
    "07:00",  # Morning rush
    "12:00",  # Midday
    "17:00",  # Evening rush
    "19:00",  # Event prime time
    "21:00",  # Late evening
    "23:00",  # Night baseline
]


def get_all_venues():
    """
    Get all venues from database.
    
    Returns:
        List of venue dictionaries
    """
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT venue_id, venue_name, latitude, longitude
                FROM venue_locations
                ORDER BY venue_id
            """)
            
            venues = []
            for row in cur.fetchall():
                venues.append({
                    'venue_id': row[0],
                    'venue_name': row[1],
                    'latitude': float(row[2]),
                    'longitude': float(row[3])
                })
            
            return venues
    finally:
        conn.close()


def split_venues_into_groups(venues: list) -> tuple:
    """
    Split venues into FOUR groups for 4-week rotation.
    
    Args:
        venues: List of all venues
        
    Returns:
        Tuple of (group1, group2, group3, group4)
    """
    total = len(venues)
    group_size = total // 4
    
    group1 = venues[0:group_size]
    group2 = venues[group_size:group_size*2]
    group3 = venues[group_size*2:group_size*3]
    group4 = venues[group_size*3:]
    
    return group1, group2, group3, group4


def get_current_baseline_group():
    """
    Determine which venue group should be collected this week.
    
    Week 1 of month (days 1-7): Group 1
    Week 2 of month (days 8-14): Group 2
    Week 3 of month (days 15-21): Group 3
    Week 4 of month (days 22-31): Group 4
    
    Returns:
        Group number (1, 2, 3, or 4) or None
    """
    now = datetime.now()
    day_of_month = now.day
    
    if 1 <= day_of_month <= 7:
        return 1
    elif 8 <= day_of_month <= 14:
        return 2
    elif 15 <= day_of_month <= 21:
        return 3
    elif 22 <= day_of_month <= 31:
        return 4
    else:
        return None


def should_collect_baseline_now():
    """
    Check if we should collect baseline traffic now.
    
    Returns:
        Tuple (should_collect: bool, group: int or None, time_slot: str or None)
    """
    group = get_current_baseline_group()
    
    if group is None:
        return False, None, None
    
    # Check if we're within 15 minutes of a time slot
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    for time_slot in BASELINE_TIME_SLOTS:
        slot_hour, slot_minute = map(int, time_slot.split(':'))
        
        # Calculate difference in minutes
        diff_minutes = abs((current_hour * 60 + current_minute) - (slot_hour * 60 + slot_minute))
        
        if diff_minutes <= 15:
            return True, group, time_slot
    
    return False, group, None


def collect_baseline_for_group(group_number: int, max_calls: int = 1000):
    """
    Collect baseline traffic for all venues in a group.
    
    Args:
        group_number: Group number (1, 2, 3, or 4)
        max_calls: Maximum API calls to make (default 1000 = safe daily limit)
        
    Returns:
        Dictionary with collection statistics
    """
    logger.info(f"Collecting baseline traffic for Group {group_number}")
    
    # Get all venues
    all_venues = get_all_venues()
    logger.info(f"Total venues in database: {len(all_venues)}")
    
    # Split into 4 groups
    group1, group2, group3, group4 = split_venues_into_groups(all_venues)
    
    groups = {1: group1, 2: group2, 3: group3, 4: group4}
    venues = groups[group_number]
    
    logger.info(f"Group {group_number}: {len(venues)} venues")
    logger.info("")
    
    total_measurements = 0
    api_calls_made = 0
    venues_processed = 0
    
    for i, venue in enumerate(venues, 1):
        logger.info(f"[{i}/{len(venues)}] {venue['venue_name']}")
        
        if api_calls_made >= max_calls:
            logger.warning(f"Reached max API calls ({max_calls}), stopping")
            break
        
        try:
            # Collect baseline traffic (TomTom Routing)
            measurements = collect_baseline_for_venue_tomtom(
                venue['venue_id'],
                venue['venue_name'],
                venue['latitude'],
                venue['longitude'],
                baseline_type='weekly'
            )
            
            for measurement in measurements:
                try:
                    insert_traffic_measurement(
                        venue_id=venue['venue_id'],
                        measurement_time=measurement['measurement_time'],
                        traffic_data=measurement,
                        event_id=None
                    )
                    total_measurements += 1
                    api_calls_made += 1
                except Exception as e:
                    logger.error(f"Error inserting measurement: {e}")
            
            venues_processed += 1
            
        except Exception as e:
            logger.error(f"Error collecting baseline for {venue['venue_name']}: {e}")
    
    logger.info("")
    logger.info(f" Processed {venues_processed}/{len(venues)} venues")
    logger.info(f" Collected {total_measurements} baseline measurements")
    logger.info(f" API calls made: {api_calls_made}")
    
    return {
        'group': group_number,
        'total_venues': len(venues),
        'venues_processed': venues_processed,
        'measurements_collected': total_measurements,
        'api_calls_made': api_calls_made
    }


def run_baseline_collection():
    """
    Main entry point for baseline collection.
    Checks if collection should run now and executes if appropriate.
    """
    logger.info("=" * 70)
    logger.info("Baseline Traffic Collection Check")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    logger.info("")
    
    should_collect, group, time_slot = should_collect_baseline_now()
    
    # Prepare log entry
    log_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'baseline_collection_log.txt'
    )
    
    if not should_collect:
        if group is None:
            logger.info("ℹ Not in a baseline collection week")
            logger.info("  Week 1 (days 1-7): Group 1")
            logger.info("  Week 2 (days 8-14): Group 2")
            logger.info("  Week 3 (days 15-21): Group 3")
            logger.info("  Week 4 (days 22-31): Group 4")
            
            # Log to file
            with open(log_file, 'a') as f:
                f.write(f"\n{datetime.now()} | Not baseline week | No collection")
        else:
            logger.info(f"ℹ Baseline collection week (Group {group}) - but not at a collection time")
            logger.info(f"  Collection times: {', '.join(BASELINE_TIME_SLOTS)}")
            
            # Log to file
            with open(log_file, 'a') as f:
                f.write(f"\n{datetime.now()} | Group {group} week | Not at collection time")
        
        logger.info("")
        logger.info("=" * 70)
        
        return {
            'collected': False,
            'reason': 'Not collection time'
        }
    
    logger.info(f" Baseline collection time!")
    logger.info(f"  Group: {group}")
    logger.info(f"  Time slot: {time_slot}")
    logger.info("")
    
    # Run collection
    try:
        stats = collect_baseline_for_group(group, max_calls=1000)
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("Baseline Collection Complete")
        logger.info("=" * 70)
        
        stats['collected'] = True
        stats['time_slot'] = time_slot
        
        # Log success to file
        with open(log_file, 'a') as f:
            f.write(f"\n{datetime.now()} | ")
            f.write(f"Group: {stats['group']} | ")
            f.write(f"Time: {time_slot} | ")
            f.write(f"Venues: {stats['venues_processed']}/{stats['total_venues']} | ")
            f.write(f"Measurements: {stats['measurements_collected']} | ")
            f.write(f"API calls: {stats['api_calls_made']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error during baseline collection: {e}")
        import traceback
        traceback.print_exc()
        
        # Log error to file
        with open(log_file, 'a') as f:
            f.write(f"\n{datetime.now()} | ERROR: {e}")
        
        return {
            'collected': False,
            'error': str(e)
        }


if __name__ == "__main__":
    """
    Test baseline scheduler
    """
    print("=" * 70)
    print("Baseline Collection Scheduler Test")
    print("=" * 70)
    print()
    
    # Show current schedule
    now = datetime.now()
    print(f"Current date: {now.strftime('%Y-%m-%d')}")
    print(f"Day of month: {now.day}")
    print()
    
    group = get_current_baseline_group()
    
    if group:
        print(f" Currently in baseline collection week")
        print(f"  Group {group} should be collected")
        print()
        
        # Show venue split
        all_venues = get_all_venues()
        group1, group2, group3, group4 = split_venues_into_groups(all_venues)
        
        print(f"Total venues: {len(all_venues)}")
        print(f"  Group 1: {len(group1)} venues")
        print(f"  Group 2: {len(group2)} venues")
        print(f"  Group 3: {len(group3)} venues")
        print(f"  Group 4: {len(group4)} venues")
        print()
    else:
        print("ℹ Not currently in a baseline collection week")
        print()
    
    # Test collection
    result = run_baseline_collection()
    
    print()
    if result['collected']:
        print(f" Collected baseline data for Group {result['group']}")
        print(f"  Venues processed: {result['venues_processed']}/{result['total_venues']}")
        print(f"  Measurements: {result['measurements_collected']}")
        print(f"  API calls: {result['api_calls_made']}")
    else:
        print(f"No collection: {result['reason']}")
    
    print()
    print("=" * 70)