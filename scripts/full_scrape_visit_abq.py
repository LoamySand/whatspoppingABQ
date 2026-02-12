# scripts/full_scrape_enhanced.py
"""
Full scrape with enhanced detail scraper.
Scrapes 10 pages and loads to database.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from scrapers.visit_abq_detail_scraper import scrape_events_with_details, validate_event
from database.db_utils import insert_events, get_event_statistics
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 70)
print("Full Event Scrape - Enhanced Detail Scraper")
print("=" * 70)
print()

start_time = datetime.now()

# Scrape 10 pages
print("Scraping 10 pages with event details...")
print("This will take 10-15 minutes due to clicking into detail pages")
print()

try:
    events = scrape_events_with_details(max_pages=10)
    
    print()
    print(f"✓ Scraped {len(events)} total events")
    print()
    
except Exception as e:
    print(f"✗ Scraping failed: {e}")
    exit(1)

# Validate
print("Validating events...")
print("-" * 70)

valid_events = []
invalid_count = 0

for event in events:
    is_valid, msg = validate_event(event)
    if is_valid:
        valid_events.append(event)
    else:
        invalid_count += 1
        logger.warning(f"Invalid event: {event.get('event_name')} - {msg}")

print(f"✓ Valid: {len(valid_events)}/{len(events)}")
if invalid_count > 0:
    print(f"⚠ Invalid: {invalid_count}")
print()

# Data quality preview
print("Data Quality Preview:")
print("-" * 70)

multi_day = sum(1 for e in valid_events if e.get('is_multi_day'))
with_times = sum(1 for e in valid_events if e.get('event_start_time'))
with_cost = sum(1 for e in valid_events if e.get('cost_description'))
with_sponsor = sum(1 for e in valid_events if e.get('sponsor'))
free_events = sum(1 for e in valid_events if e.get('cost_min') == 0)

print(f"Multi-day events: {multi_day} ({multi_day*100//len(valid_events) if valid_events else 0}%)")
print(f"Events with times: {with_times} ({with_times*100//len(valid_events) if valid_events else 0}%)")
print(f"Events with cost info: {with_cost} ({with_cost*100//len(valid_events) if valid_events else 0}%)")
print(f"Events with sponsors: {with_sponsor} ({with_sponsor*100//len(valid_events) if valid_events else 0}%)")
print(f"Free events: {free_events}")
print()

# Load to database
print("Loading to database...")
print("-" * 70)

try:
    count = insert_events(valid_events)
    print(f"✓ Loaded {count} events to database")
    print()
except Exception as e:
    print(f"✗ Database load failed: {e}")
    exit(1)

# Final statistics
print("Database Statistics:")
print("-" * 70)

stats = get_event_statistics()

print(f"Total events: {stats['total_events']}")
print(f"Multi-day events: {stats['multi_day_events']} ({stats['multi_day_events']*100//stats['total_events'] if stats['total_events'] else 0}%)")
print(f"Events with times: {stats['events_with_times']} ({stats['events_with_times']*100//stats['total_events'] if stats['total_events'] else 0}%)")
print(f"Events with cost: {stats['events_with_cost']} ({stats['events_with_cost']*100//stats['total_events'] if stats['total_events'] else 0}%)")
print(f"Free events: {stats['free_events']}")
print(f"Events with sponsors: {stats['events_with_sponsors']} ({stats['events_with_sponsors']*100//stats['total_events'] if stats['total_events'] else 0}%)")

if 'avg_cost_min' in stats:
    print(f"Average cost: ${stats['avg_cost_min']:.2f} - ${stats['avg_cost_max']:.2f}")

print()
print("Top 10 Categories:")
for cat, count in list(stats['by_category'].items())[:10]:
    print(f"  {cat}: {count}")

print()

# Execution time
end_time = datetime.now()
duration = end_time - start_time
print(f"Execution time: {duration}")

print()
print("=" * 70)
print("Full Scrape Complete!")
print("=" * 70)