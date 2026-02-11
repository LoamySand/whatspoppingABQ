# flows/deploy_ingestion.py
"""
Deploy the event ingestion flow with scheduling.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from flows.ingest_events import event_ingestion_flow

if __name__ == "__main__":
    # Deploy the flow with a daily schedule
    print("Deploying event ingestion flow...")
    print("This will run the flow daily at 6:00 AM")
    print("Press Ctrl+C to stop")
    print()
    
    deployment = event_ingestion_flow.serve(
        name="daily-event-ingestion",
        cron="0 6 * * *",  # Run daily at 6 AM
        parameters={"max_pages": 3},
        description="Daily ingestion of events from Visit Albuquerque"
    )