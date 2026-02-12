# flows/ingest_events_enhanced.py
"""
Enhanced Prefect flow for event ingestion with detailed scraping.
"""

from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from scrapers.visit_abq_detail_scraper import scrape_events_with_details, validate_event
from database.db_utils import (
    get_event_count, 
    insert_events, 
    get_event_statistics,
    get_multi_day_events
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@task(retries=2, retry_delay_seconds=300)
def scrape_events_task(max_pages: int = 3):
    """
    Scrape events from Visit Albuquerque with detail page extraction.
    
    Args:
        max_pages: Number of pages to scrape (default 3)
        
    Returns:
        List of event dictionaries
    """
    logger.info(f"Starting scrape of {max_pages} pages with detail extraction")
    
    events = scrape_events_with_details(max_pages=max_pages)
    
    logger.info(f"Scraped {len(events)} events")
    
    # Log sample event
    if events:
        logger.info(f"Sample event: {events[0].get('event_name')}")
        logger.info(f"  Start: {events[0].get('event_start_date')} {events[0].get('event_start_time')}")
        logger.info(f"  Multi-day: {events[0].get('is_multi_day')}")
        logger.info(f"  Category: {events[0].get('category')}")
        logger.info(f"  Cost: {events[0].get('cost_description')}")
    
    return events


@task
def validate_events_task(events: list):
    """
    Validate scraped events.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        List of valid event dictionaries
    """
    logger.info(f"Validating {len(events)} events")
    
    valid_events = []
    invalid_events = []
    
    for event in events:
        is_valid, message = validate_event(event)
        
        if is_valid:
            valid_events.append(event)
        else:
            invalid_events.append({
                'event': event.get('event_name'),
                'reason': message
            })
            logger.warning(f"Invalid event: {event.get('event_name')} - {message}")
    
    logger.info(f"Valid events: {len(valid_events)}/{len(events)}")
    
    if invalid_events:
        logger.warning(f"Invalid events: {len(invalid_events)}")
        for inv in invalid_events[:5]:  # Log first 5
            logger.warning(f"  - {inv['event']}: {inv['reason']}")
    
    return valid_events


@task(retries=1, retry_delay_seconds=60)
def load_events_task(events: list):
    """
    Load events into PostgreSQL database.
    
    Args:
        events: List of valid event dictionaries
        
    Returns:
        Dictionary with load statistics
    """
    logger.info(f"Loading {len(events)} events to database")
    
    # Get before count
    count_before = get_event_count()
    logger.info(f"Events in database before load: {count_before}")
    
    # Insert events
    inserted = insert_events(events)
    
    # Get after count
    count_after = get_event_count()
    logger.info(f"Events in database after load: {count_after}")
    
    # Calculate statistics
    new_events = count_after - count_before
    updated_events = inserted - new_events
    
    load_stats = {
        'events_loaded': inserted,
        'new_events': max(0, new_events),
        'updated_events': max(0, updated_events),
        'total_in_db': count_after
    }
    
    logger.info(f"New events: {load_stats['new_events']}")
    logger.info(f"Updated events: {load_stats['updated_events']}")
    
    return load_stats

@task(retries=1, retry_delay_seconds=60)
def geocode_venues_task():
    """
    Geocode venues for events that don't have coordinates.
    
    Returns:
        Number of venues geocoded
    """
    logger.info("Geocoding venues for new events")
    
    from database.db_utils import geocode_and_link_events
    
    geocoded_count = geocode_and_link_events()
    
    logger.info(f"Geocoded {geocoded_count} venues")
    
    return geocoded_count

@task
def generate_summary_task(load_stats: dict):
    """
    Generate summary statistics and display results.
    
    Args:
        load_stats: Dictionary with load statistics
        
    Returns:
        Dictionary with comprehensive summary
    """
    logger.info("Generating summary statistics")
    
    # Get comprehensive stats
    stats = get_event_statistics()
    
    # Get multi-day events
    multi_day_events = get_multi_day_events()
    
    # Build summary
    summary = {
        'load_stats': load_stats,
        'database_stats': stats,
        'multi_day_count': len(multi_day_events)
    }
    
    # Display summary
    print("\n" + "=" * 70)
    print("EVENT INGESTION SUMMARY")
    print("=" * 70)
    print()
    
    print("Load Statistics:")
    print(f"  Events processed: {load_stats['events_loaded']}")
    print(f"  New events: {load_stats['new_events']}")
    print(f"  Updated events: {load_stats['updated_events']}")
    print(f"  Total in database: {load_stats['total_in_db']}")
    print()
    
    print("Data Quality:")
    print(f"  Multi-day events: {stats['multi_day_events']} ({stats['multi_day_events']*100//stats['total_events'] if stats['total_events'] else 0}%)")
    print(f"  Events with times: {stats['events_with_times']} ({stats['events_with_times']*100//stats['total_events'] if stats['total_events'] else 0}%)")
    print(f"  Events with cost: {stats['events_with_cost']} ({stats['events_with_cost']*100//stats['total_events'] if stats['total_events'] else 0}%)")
    print(f"  Free events: {stats['free_events']}")
    print(f"  Events with sponsors: {stats['events_with_sponsors']} ({stats['events_with_sponsors']*100//stats['total_events'] if stats['total_events'] else 0}%)")
    print()
    
    if 'avg_cost_min' in stats:
        print(f"  Average cost: ${stats['avg_cost_min']:.2f} - ${stats['avg_cost_max']:.2f}")
        print()
    
    print("Top 5 Categories:")
    for cat, count in list(stats['by_category'].items())[:5]:
        pct = count * 100 // stats['total_events'] if stats['total_events'] else 0
        print(f"  {cat}: {count} ({pct}%)")
    
    print()
    
    if multi_day_events:
        print("Sample Multi-Day Events:")
        for event in multi_day_events[:3]:
            print(f"  - {event['event_name']}")
            print(f"    {event['event_start_date']} to {event['event_end_date']} ({event['duration_days']} days)")
    
    print()
    print("=" * 70)
    
    return summary


@flow(name="Event Ingestion Pipeline", log_prints=True)
def event_ingestion_flow_enhanced(max_pages: int = 3):
    """
    Main Prefect flow for enhanced event ingestion.
    
    Workflow:
        1. Scrape events with detail extraction
        2. Validate event data
        3. Load to PostgreSQL
        4. Geocode venues and link events
        5. Generate summary statistics
    
    Args:
        max_pages: Number of pages to scrape (default 3)
        
    Returns:
        Summary dictionary
    """
    logger.info(f"Starting enhanced event ingestion flow (max_pages={max_pages})")
    
    # Task 1: Scrape
    events = scrape_events_task(max_pages=max_pages)
    
    # Task 2: Validate
    valid_events = validate_events_task(events)
    
    # Task 3: Load
    load_stats = load_events_task(valid_events)
    
    # Task 4: Geocode venues
    geocoded_count = geocode_venues_task()
    
    # Task 5: Summarize
    summary = generate_summary_task(load_stats)
    summary['geocoded_venues'] = geocoded_count
    
    logger.info("Enhanced event ingestion flow complete")
    
    return summary


if __name__ == "__main__":
    """
    Run the enhanced flow
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced event ingestion flow')
    parser.add_argument('--pages', type=int, default=3, help='Number of pages to scrape')
    args = parser.parse_args()
    
    # Run flow
    result = event_ingestion_flow_enhanced(max_pages=args.pages)