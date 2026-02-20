"""
Prefect flows for traffic collection
"""

from prefect import flow, task
from datetime import timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.tomtom_event_traffic_collector import run_tomtom_event_collection
from collectors.baseline_schedule import run_baseline_collection


@task(retries=3, retry_delay_seconds=60)
def collect_event_traffic():
    """
    Task to collect event traffic
    """
    from datetime import datetime
    print(f"[TASK] Calling run_tomtom_event_collection at {datetime.now()}")
    
    stats = run_tomtom_event_collection(max_calls=50)
    
    print(f"[TASK] Collection returned: {stats}")
    
    return {
        'events_checked': stats['events_checked'],
        'events_collected': stats['events_collected'],
        'measurements': stats['measurements_collected'],
        'api_calls': stats['api_calls_made']
    }


@task(retries=3, retry_delay_seconds=60)
def collect_baseline_traffic():
    """
    Task to collect baseline traffic
    """
    result = run_baseline_collection()
    
    if result['collected']:
        return {
            'group': result['group'],
            'venues_processed': result['venues_processed'],
            'measurements': result['measurements_collected'],
            'api_calls': result['api_calls_made']
        }
    else:
        return {
            'skipped': True,
            'reason': result.get('reason', 'Not collection time')
        }


@flow(name="Event Traffic Collection")
def event_traffic_flow():
    """
    Flow to collect traffic for events (runs every 30 minutes)
    """
    from datetime import datetime
    print(f"[START] Event traffic flow started at {datetime.now()}")
    
    result = collect_event_traffic()
    
    print(f"[OK] Event traffic collection complete")
    print(f"  Events checked: {result['events_checked']}")
    print(f"  Events collected: {result['events_collected']}")
    print(f"  Measurements: {result['measurements']}")
    print(f"  API calls: {result['api_calls']}")
    
    print(f"[END] Event traffic flow finished at {datetime.now()}")
    
    return result


@flow(name="Baseline Traffic Collection")
def baseline_traffic_flow():
    """
    Flow to collect baseline traffic (runs 6 times/day)
    """
    result = collect_baseline_traffic()
    
    if result.get('skipped'):
        print(f"Baseline collection skipped: {result['reason']}")
    else:
        print(f"[OK] Baseline traffic collection complete")
        print(f"  Group: {result['group']}")
        print(f"  Venues processed: {result['venues_processed']}")
        print(f"  Measurements: {result['measurements']}")
        print(f"  API calls: {result['api_calls']}")
    
    return result


if __name__ == "__main__":
    """
    Test the flows
    """
    print("Testing Event Traffic Flow:")
    print("=" * 70)
    event_traffic_flow()
    
    print()
    print()
    
    print("Testing Baseline Traffic Flow:")
    print("=" * 70)
    baseline_traffic_flow()