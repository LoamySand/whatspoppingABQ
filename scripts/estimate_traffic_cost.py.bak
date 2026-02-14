"""
Estimate traffic collection costs for actual events in database.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
from collectors.traffic_collection_rules import get_collection_plan, estimate_monthly_api_calls

print("=" * 70)
print("Traffic Collection Cost Estimate")
print("=" * 70)
print()

# Get all events from database
conn = get_connection()

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                event_id,
                event_name,
                category,
                event_start_time,
                is_multi_day
            FROM events
        """)
        
        events = []
        for row in cur.fetchall():
            events.append({
                'event_id': row[0],
                'event_name': row[1],
                'category': row[2],
                'event_start_time': row[3],
                'is_multi_day': row[4]
            })
finally:
    conn.close()

print(f"Total events in database: {len(events)}")
print()

# Get estimate
estimate = estimate_monthly_api_calls(events)

print("Monthly Estimate:")
print("-" * 70)
print(f"Total API calls: {estimate['total_calls']}")
print(f"Events with traffic collection: {estimate['events_processed'] - estimate['events_skipped']}")
print(f"Events skipped (no time): {estimate['events_skipped']}")
print()

print("Calls by event type:")
for event_type, calls in estimate['by_type'].items():
    print(f"  {event_type}: {calls} calls")

print()
print(f"Estimated cost: ${estimate['estimated_cost']}/month")
print(f"Free tier: $200/month")
print(f"Remaining: ${200 - estimate['estimated_cost']:.2f}")
print()

if estimate['estimated_cost'] < 200:
    print("✅ WITHIN FREE TIER")
else:
    print("⚠️  EXCEEDS FREE TIER")

print()
print("=" * 70)