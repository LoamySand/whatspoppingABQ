# scripts/analyze_event_times.py
"""
Analyze event data to see what we have for times.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection

print("=" * 70)
print("Event Time Analysis")
print("=" * 70)
print()

conn = get_connection()

try:
    # Check time data
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(event_time) as with_time,
                COUNT(expected_attendance) as with_attendance
            FROM events
        """)
        
        total, with_time, with_attendance = cur.fetchone()
        
        print(f"Total events: {total}")
        print(f"Events with time: {with_time} ({with_time*100//total if total else 0}%)")
        print(f"Events with attendance: {with_attendance} ({with_attendance*100//total if total else 0}%)")
        print()
        
        # Category breakdown
        cur.execute("""
            SELECT 
                category,
                COUNT(*) as count,
                COUNT(event_time) as with_time
            FROM events
            GROUP BY category
            ORDER BY count DESC
        """)
        
        print("Events by Category:")
        print("-" * 70)
        for row in cur.fetchall():
            category, count, time_count = row
            print(f"  {category:20s}: {count:3d} events, {time_count:3d} with time")
        
        print()
        
        # Sample events
        cur.execute("""
            SELECT event_name, category, event_date, event_time
            FROM events
            ORDER BY event_date
            LIMIT 10
        """)
        
        print("Sample Events:")
        print("-" * 70)
        for row in cur.fetchall():
            name, category, date, time = row
            print(f"  {name[:40]:40s} | {category:15s} | {date} | {time or 'NO TIME'}")

finally:
    conn.close()

print()
print("=" * 70)