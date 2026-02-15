"""
Backfill event_id for existing traffic measurements.
Matches traffic measurements to events based on:
- Same venue
- Traffic measurement time within event collection window (±2 hours)
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
from datetime import datetime

print("=" * 70)
print("Backfill Event IDs for Traffic Measurements")
print("=" * 70)
print()

conn = get_connection()

try:
    # Step 1: Find traffic measurements without event_id that are NOT baseline
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) 
            FROM traffic_measurements 
            WHERE event_id IS NULL 
              AND is_baseline = FALSE
        """)
        
        unlinked_count = cur.fetchone()[0]
        
        print(f"Traffic measurements without event_id: {unlinked_count}")
        print()
        
        if unlinked_count == 0:
            print(" All non-baseline traffic measurements already have event_id!")
            exit(0)
    
    # Step 2: Match traffic to events
    print("Matching traffic measurements to events...")
    print("-" * 70)
    
    with conn.cursor() as cur:
        # Find matches based on:
        # 1. Same venue
        # 2. Measurement time within ±2 hours of event start time
        
        query = """
            WITH potential_matches AS (
                SELECT 
                    tm.measurement_id,
                    tm.venue_id,
                    tm.measurement_time,
                    e.event_id,
                    e.event_name,
                    e.event_start_date,
                    e.event_start_time,
                    e.event_start_date + e.event_start_time as event_datetime,
                    EXTRACT(EPOCH FROM (
                        tm.measurement_time - 
                        (e.event_start_date + e.event_start_time)
                    )) / 3600 as hours_from_event,
                    ROW_NUMBER() OVER (
                        PARTITION BY tm.measurement_id 
                        ORDER BY ABS(EXTRACT(EPOCH FROM (
                            tm.measurement_time - 
                            (e.event_start_date + e.event_start_time)
                        )))
                    ) as match_rank
                FROM traffic_measurements tm
                JOIN events e ON tm.venue_id = e.venue_id
                WHERE tm.event_id IS NULL
                  AND tm.is_baseline = FALSE
                  AND e.event_start_time IS NOT NULL
                  AND tm.measurement_time BETWEEN 
                      (e.event_start_date + e.event_start_time - INTERVAL '2 hours') AND
                      (e.event_start_date + e.event_start_time + INTERVAL '2 hours')
            )
            SELECT 
                measurement_id,
                event_id,
                event_name,
                event_datetime,
                measurement_time,
                hours_from_event
            FROM potential_matches
            WHERE match_rank = 1  -- Only take closest match if multiple events
            ORDER BY measurement_time
        """
        
        cur.execute(query)
        matches = cur.fetchall()
        
        print(f"Found {len(matches)} traffic measurements that can be linked to events")
        print()
        
        if len(matches) == 0:
            print(" No matches found!")
            print()
            print("Possible reasons:")
            print("  - Traffic measurements are outside ±2 hour window of events")
            print("  - Venue IDs don't match")
            print("  - Events don't have start times")
            exit(0)
        
        # Show sample matches
        print("Sample matches (first 10):")
        print("-" * 70)
        for i, match in enumerate(matches[:10], 1):
            meas_id, event_id, event_name, event_dt, meas_time, hours_diff = match
            print(f"{i}. Measurement ID {meas_id} → Event ID {event_id}")
            print(f"   Event: {event_name}")
            print(f"   Event time: {event_dt}")
            print(f"   Measurement: {meas_time} ({hours_diff:+.1f} hours from event)")
            print()
        
        if len(matches) > 10:
            print(f"... and {len(matches) - 10} more")
            print()
    
    # Step 3: Ask for confirmation
    print("=" * 70)
    response = input(f"Update {len(matches)} traffic measurements with event_id? (y/n): ")
    print()
    
    if response.lower() != 'y':
        print("Cancelled. No changes made.")
        exit(0)
    
    # Step 4: Update the records
    print("Updating traffic measurements...")
    print("-" * 70)
    
    updated_count = 0
    
    with conn.cursor() as cur:
        for match in matches:
            meas_id, event_id, event_name, event_dt, meas_time, hours_diff = match
            
            cur.execute("""
                UPDATE traffic_measurements
                SET event_id = %s
                WHERE measurement_id = %s
            """, (event_id, meas_id))
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"  Updated {updated_count}/{len(matches)}...")
        
        conn.commit()
    
    print(f" Updated {updated_count} traffic measurements")
    print()
    
    # Step 5: Verify
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) 
            FROM traffic_measurements 
            WHERE event_id IS NULL 
              AND is_baseline = FALSE
        """)
        
        remaining = cur.fetchone()[0]
        
        print("Verification:")
        print(f"  Before: {unlinked_count} unlinked")
        print(f"  Updated: {updated_count}")
        print(f"  After: {remaining} unlinked")
        print()
        
        if remaining > 0:
            print(f" {remaining} measurements still unlinked")
            print("These are likely measurements outside event windows")
        else:
            print(" All non-baseline measurements now linked to events!")

finally:
    conn.close()

print()
print("=" * 70)
print("Backfill Complete")
print("=" * 70)