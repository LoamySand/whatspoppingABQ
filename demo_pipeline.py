# demo_pipeline.py
"""
Quick demo of the event pipeline for presentations/interviews.
Runs a simplified version with clear output.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from flows.ingest_events import event_ingestion_flow
from database.db_utils import get_event_count, get_category_counts

print()
print("=" * 70)
print("          ALBUQUERQUE EVENT ANALYTICS PIPELINE")
print("                      DEMO")
print("=" * 70)
print()
print("This pipeline:")
print("  1. Scrapes events from Visit Albuquerque")
print("  2. Validates data quality")
print("  3. Loads events into PostgreSQL")
print("  4. Generates summary statistics")
print()
print("Technology Stack:")
print("  • Python 3.11")
print("  • Selenium (web scraping)")
print("  • PostgreSQL (data warehouse)")
print("  • Prefect (orchestration)")
print()
input("Press Enter to start the pipeline...")
print()

# Show before state
print("=" * 70)
print("BEFORE STATE")
print("=" * 70)
before_count = get_event_count()
print(f"Events in database: {before_count}")
print()

# Run pipeline (1 page for quick demo)
print("=" * 70)
print("RUNNING PIPELINE...")
print("=" * 70)
result = event_ingestion_flow(max_pages=1)
print()

# Show after state
print("=" * 70)
print("AFTER STATE")
print("=" * 70)
after_count = get_event_count()
print(f"Events in database: {after_count}")
print(f"Events added/updated: {after_count - before_count}")
print()

categories = get_category_counts()
print("Category Breakdown:")
for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  • {cat}: {count}")
print()

print("=" * 70)
print("DEMO COMPLETE!")
print("=" * 70)
print()