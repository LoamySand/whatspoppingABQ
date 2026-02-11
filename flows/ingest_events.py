# flows/ingest_events.py
"""
Prefect flow for ingesting events from Visit Albuquerque.

This flow orchestrates:
1. Scraping events from the website
2. Validating event data
3. Loading events into PostgreSQL database
"""

from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
import sys
import logging
from typing import List, Dict

# Add project to path
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from scrapers.visit_abq_scraper import scrape_events_selenium, validate_event
from database.db_utils import insert_events, get_event_count, get_category_counts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@task(
    name="Scrape Events",
    description="Scrape events from Visit Albuquerque website",
    retries=2,
    retry_delay_seconds=300,
    log_prints=True
)
def scrape_events_task(max_pages: int = 3) -> List[Dict]:
    """
    Task to scrape events from Visit Albuquerque.
    
    Args:
        max_pages: Number of pages to scrape
        
    Returns:
        List of event dictionaries
    """
    print(f"Starting event scraping (max {max_pages} pages)...")
    
    try:
        events = scrape_events_selenium(max_pages=max_pages)
        
        print(f"✓ Successfully scraped {len(events)} events")
        
        if events:
            # Show sample
            print(f"\nSample events:")
            for event in events[:3]:
                print(f"  - {event['event_name']}")
        
        return events
        
    except Exception as e:
        print(f"✗ Error during scraping: {e}")
        raise


@task(
    name="Validate Events",
    description="Validate scraped event data",
    log_prints=True
)
def validate_events_task(events: List[Dict]) -> List[Dict]:
    """
    Task to validate scraped events.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        List of valid event dictionaries
    """
    print(f"Validating {len(events)} events...")
    
    valid_events = []
    invalid_events = []
    
    for event in events:
        is_valid, message = validate_event(event)
        if is_valid:
            valid_events.append(event)
        else:
            invalid_events.append((event.get('event_name', 'Unknown'), message))
    
    print(f"✓ Valid events: {len(valid_events)}")
    print(f"✗ Invalid events: {len(invalid_events)}")
    
    if invalid_events:
        print("\nInvalid events (first 5):")
        for name, msg in invalid_events[:5]:
            print(f"  - {name}: {msg}")
    
    return valid_events


@task(
    name="Load Events to Database",
    description="Insert events into PostgreSQL database",
    retries=1,
    retry_delay_seconds=60,
    log_prints=True
)
def load_events_task(events: List[Dict]) -> Dict:
    """
    Task to load events into database.
    
    Args:
        events: List of valid event dictionaries
        
    Returns:
        Dictionary with load statistics
    """
    if not events:
        print("⚠️ No events to load")
        return {
            'events_loaded': 0,
            'db_count_before': 0,
            'db_count_after': 0
        }
    
    print(f"Loading {len(events)} events to database...")
    
    try:
        # Get count before
        count_before = get_event_count()
        print(f"Events in database before: {count_before}")
        
        # Insert events
        loaded = insert_events(events)
        
        # Get count after
        count_after = get_event_count()
        print(f"Events in database after: {count_after}")
        
        # Calculate stats
        new_events = count_after - count_before
        updated_events = loaded - new_events
        
        print(f"✓ Loaded {loaded} events ({new_events} new, {updated_events} updated)")
        
        return {
            'events_loaded': loaded,
            'new_events': new_events,
            'updated_events': updated_events,
            'db_count_before': count_before,
            'db_count_after': count_after
        }
        
    except Exception as e:
        print(f"✗ Error loading to database: {e}")
        raise


@task(
    name="Generate Summary Report",
    description="Generate summary statistics",
    log_prints=True
)
def generate_summary_task(load_stats: Dict) -> Dict:
    """
    Task to generate summary report.
    
    Args:
        load_stats: Statistics from load task
        
    Returns:
        Dictionary with summary information
    """
    print("\n" + "=" * 60)
    print("Pipeline Summary")
    print("=" * 60)
    
    print(f"\nLoad Statistics:")
    print(f"  Events loaded: {load_stats.get('events_loaded', 0)}")
    print(f"  New events: {load_stats.get('new_events', 0)}")
    print(f"  Updated events: {load_stats.get('updated_events', 0)}")
    print(f"  Total in database: {load_stats.get('db_count_after', 0)}")
    
    # Get category breakdown
    try:
        categories = get_category_counts()
        print(f"\nEvents by Category:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")
    except Exception as e:
        print(f"Could not get category breakdown: {e}")
    
    print("\n" + "=" * 60)
    
    return {
        'load_stats': load_stats,
        'categories': categories if 'categories' in locals() else {}
    }


@flow(
    name="Visit Albuquerque Event Pipeline",
    description="Scrape, validate, and load events from Visit Albuquerque",
    log_prints=True
)
def event_ingestion_flow(max_pages: int = 3):
    """
    Main pipeline flow for ingesting Visit Albuquerque events.
    
    Args:
        max_pages: Number of pages to scrape (default: 3)
    """
    print("\n" + "=" * 60)
    print("Visit Albuquerque Event Ingestion Pipeline")
    print("=" * 60)
    print()
    
    # Task 1: Scrape events
    events = scrape_events_task(max_pages=max_pages)
    
    # Task 2: Validate events
    valid_events = validate_events_task(events)
    
    # Task 3: Load to database
    load_stats = load_events_task(valid_events)
    
    # Task 4: Generate summary
    summary = generate_summary_task(load_stats)
    
    print("\n✅ Pipeline completed successfully!")
    
    return summary


if __name__ == "__main__":
    """
    Run the flow when executed directly.
    """
    # Run with default settings (3 pages)
    result = event_ingestion_flow(max_pages=3)