# scripts/validate_collection.py
"""
Validate that data collection is working properly
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
from datetime import datetime

print("=" * 70)
print("Data Collection Validation Report")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

conn = get_connection()

try:
    # 1. Collection Status Summary
    print("COLLECTION STATUS SUMMARY")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM collection_status_summary")
        row = cur.fetchone()
        cols = [desc[0] for desc in cur.description]
        
        for col, val in zip(cols, row):
            print(f"{col:30s}: {val}")
    
    print()
    print()
    
    # 2. Data Quality Issues
    print("DATA QUALITY ISSUES")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM data_quality_check WHERE count > 0")
        
        has_issues = False
        for row in cur.fetchall():
            issue, count, impact = row
            print(f"⚠ {issue}: {count}")
            print(f"   Impact: {impact}")
            print()
            has_issues = True
        
        if not has_issues:
            print("✓ No data quality issues found!")
    
    print()
    print()
    
    # 3. Recent Activity
    print("RECENT COLLECTION ACTIVITY (Last 6 Hours)")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                collection_hour,
                measurements,
                baseline_count,
                event_count,
                data_source
            FROM recent_collection_activity
            LIMIT 6
        """)
        
        rows = cur.fetchall()
        
        if rows:
            print(f"{'Hour':<20} {'Total':>8} {'Baseline':>10} {'Event':>8} {'Source':<12}")
            print("-" * 70)
            
            for row in rows:
                hour, total, baseline, event, source = row
                print(f"{str(hour):<20} {total:>8} {baseline:>10} {event:>8} {source:<12}")
        else:
            print("⚠ No measurements in last 6 hours!")
    
    print()
    print()
    
    # 4. Events Missing Traffic
    print("EVENTS MISSING TRAFFIC DATA (Next 7 Days)")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                event_name,
                event_start_date,
                event_start_time,
                event_status,
                missing_reason
            FROM events_missing_traffic
            WHERE event_status IN ('today', 'future')
              AND days_until_event <= 7
            LIMIT 10
        """)
        
        rows = cur.fetchall()
        
        if rows:
            for row in rows:
                name, date, time, status, reason = row
                print(f"• {name[:40]}")
                print(f"  {date} at {time} ({status})")
                print(f"  Reason: {reason}")
                print()
        else:
            print("✓ All upcoming events have traffic data!")
    
    print()
    print()
    
    # 5. Venues Missing Baseline
    print("VENUES MISSING BASELINE DATA")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                venue_name,
                total_baseline_measurements,
                days_covered,
                hours_covered,
                baseline_status
            FROM venues_missing_baseline
            WHERE baseline_status != 'Good coverage'
            LIMIT 10
        """)
        
        rows = cur.fetchall()
        
        if rows:
            for row in rows:
                name, measurements, days, hours, status = row
                print(f"• {name[:40]}")
                print(f"  Measurements: {measurements}, Days: {days}/7, Hours: {hours}/6")
                print(f"  Status: {status}")
                print()
        else:
            print("✓ All venues have good baseline coverage!")
    
    print()
    print()
    
    # 6. API Usage (Last 7 Days)
    print("API USAGE (Last 7 Days)")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                date,
                data_source,
                api_calls,
                gogogle_maps_calls,
                tomtom_calls,
            FROM api_usage_by_day
            WHERE date >= CURRENT_DATE - 7
            ORDER BY date DESC, data_source
        """)
        
        print(f"{'Date':<12} {'Source':<12} {'Calls':>8} {'Google Maps':>12} {'TomTom':>8}")
        print("-" * 70)

finally:
    conn.close()

print()
print("=" * 70)
print("Validation Complete")
print("=" * 70)