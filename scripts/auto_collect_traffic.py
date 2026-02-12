"""
Automated traffic collection script.
Run this hourly to collect traffic for upcoming events.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from collectors.event_traffic_collector import run_scheduled_collection
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("Automated Event Traffic Collection")
print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

# Run collection
stats = run_scheduled_collection(max_calls=50)

# Log to file
with open('traffic_collection_log.txt', 'a') as f:
    f.write(f"\n{datetime.now()} | ")
    f.write(f"Checked: {stats['events_checked']} | ")
    f.write(f"Collected: {stats['events_collected']} | ")
    f.write(f"Measurements: {stats['measurements_collected']} | ")
    f.write(f"API calls: {stats['api_calls_made']}")

print()
print("=" * 70)
print("Collection complete!")
print("See traffic_collection_log.txt for history")
print("=" * 70)