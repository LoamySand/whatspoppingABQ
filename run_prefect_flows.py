# run_prefect_flows.py
"""
Unified Prefect flow server
Runs ALL flows: traffic collection + event scraping
"""

import sys
import os

# Set Prefect API URL BEFORE importing anything
os.environ['PREFECT_API_URL'] = 'http://127.0.0.1:4200/api'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prefect import serve
from datetime import timedelta
import time

# Import all flows
from flows.collect_traffic import event_traffic_flow, baseline_traffic_flow
from flows.ingest_events import event_ingestion_flow_enhanced

# Verify server is reachable before starting
def wait_for_server(max_attempts=30):
    """Wait for Prefect server to be ready"""
    import requests
    
    print("Checking server connection...")
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get("http://127.0.0.1:4200/api/health", timeout=2)
            if response.status_code == 200:
                print(f"[OK] Connected to Prefect server (attempt {attempt})")
                return True
        except:
            if attempt % 5 == 0:
                print(f"  Still waiting for server... (attempt {attempt}/{max_attempts})")
            time.sleep(2)
    
    print("[ERROR] Could not connect to Prefect server")
    print("Make sure 'prefect server start' is running")
    return False

if __name__ == "__main__":
    print("=" * 70)
    print("Starting ALL Prefect Flows")
    print("=" * 70)
    print()
    
    # Wait for server
    if not wait_for_server():
        sys.exit(1)
    
    print()
    print("Traffic Collection:")
    print("  - Event Traffic: Every 30 minutes")
    print("  - Baseline Traffic: 6 times per day (7am, 12pm, 5pm, 7pm, 9pm, 11pm)")
    print()
    print("Event Scraping:")
    print("  - Weekly: Mondays at 9am")
    print()
    print("Monitor at: http://localhost:4200")
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Serve ALL flows
    serve(
        # ===== TRAFFIC COLLECTION =====
        
        # Event traffic - every 30 minutes
        event_traffic_flow.to_deployment(
            name="event-traffic",
            interval=timedelta(minutes=30)
        ),
        
        # Baseline traffic - 6 times per day
        baseline_traffic_flow.to_deployment(
            name="baseline-7am",
            cron="0 7 * * *",
            timezone="America/Denver"
        ),
        baseline_traffic_flow.to_deployment(
            name="baseline-12pm",
            cron="0 12 * * *",
            timezone="America/Denver"
        ),
        baseline_traffic_flow.to_deployment(
            name="baseline-5pm",
            cron="0 17 * * *",
            timezone="America/Denver"
        ),
        baseline_traffic_flow.to_deployment(
            name="baseline-7pm",
            cron="0 19 * * *",
            timezone="America/Denver"
        ),
        baseline_traffic_flow.to_deployment(
            name="baseline-9pm",
            cron="0 21 * * *",
            timezone="America/Denver"
        ),
        baseline_traffic_flow.to_deployment(
            name="baseline-11pm",
            cron="0 23 * * *",
            timezone="America/Denver"
        ),
        
        # ===== EVENT SCRAPING =====
        
        # Event scraping - weekly on Mondays at 9am
        event_ingestion_flow_enhanced.to_deployment(
            name="event-scraping-weekly",
            cron="0 9 * * 1",  # Monday 9am
            timezone="America/Denver"
        )
    )