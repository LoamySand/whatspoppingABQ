# flows/deploy_ingestion.py
"""
Deploy the event ingestion flow with scheduling.
Run this once to register the deployment with the Prefect server.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flows.ingest_events import event_ingestion_flow

if __name__ == "__main__":
    print("Registering deployment with Prefect server...")

    event_ingestion_flow.from_source(
        source="/home/pi/whatspoppingABQ", entrypoint="flows/ingest_events.py:event_ingestion_flow"
    ).deploy(
        name="daily-event-ingestion",
        work_pool_name="default-agent-pool",
        cron="0 6 * * *",
        parameters={"max_pages": 3},
        description="Daily ingestion of events from Visit Albuquerque",
    )

    print("Deployment registered successfully!")
    print("Check the Prefect UI deployments tab.")
