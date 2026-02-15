# scripts/auto_collect_traffic_tomtom.py
"""
Automated traffic collection script using TomTom API.
Run this every 30 minutes to collect traffic for upcoming events.
"""

import sys
import os

# Add project root to path (more robust)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from collectors.tomtom_event_traffic_collector import run_tomtom_event_collection
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

print("=" * 70)
print("Automated Event Traffic Collection (TomTom)")
print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Working directory: {os.getcwd()}")
print(f"Project root: {project_root}")
print("=" * 70)
print()

try:
    # Run collection
    stats = run_tomtom_event_collection(max_calls=50)

    # Log to file
    log_file = os.path.join(project_root, 'traffic_collection_log.txt')
    with open(log_file, 'a') as f:
        f.write(f"\n{datetime.now()} | ")
        f.write(f"Checked: {stats['events_checked']} | ")
        f.write(f"Collected: {stats['events_collected']} | ")
        f.write(f"Measurements: {stats['measurements_collected']} | ")
        f.write(f"API calls: {stats['api_calls_made']}")

    print()
    print("=" * 70)
    print("Collection complete!")
    print(f"See {log_file} for history")
    print("=" * 70)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    
    # Log error
    log_file = os.path.join(project_root, 'traffic_collection_log.txt')
    with open(log_file, 'a') as f:
        f.write(f"\n{datetime.now()} | ERROR: {e}")
    
    sys.exit(1)