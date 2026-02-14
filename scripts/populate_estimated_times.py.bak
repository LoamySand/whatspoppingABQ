# scripts/populate_estimated_times.py
"""
Populate estimated event times based on category and typical patterns.
This is a temporary fix until we enhance the scraper.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Typical event times by category
EVENT_TIME_DEFAULTS = {
    'Sports': '19:00:00',           # 7 PM (evening games)
    'Sports - Baseball': '18:35:00', # 6:35 PM (typical Isotopes start)
    'Sports - Basketball': '19:00:00', # 7 PM
    'Music': '20:00:00',            # 8 PM (concerts)
    'Festival': '10:00:00',         # 10 AM (festivals start early)
    'Arts & Culture': '19:00:00',   # 7 PM
    'Theater': '19:30:00',          # 7:30 PM (typical curtain time)
    'Food & Drink': '18:00:00',     # 6 PM
    'Market': '09:00:00',           # 9 AM (farmers markets)
    'General': '18:00:00',          # 6 PM (generic default)
}

# Estimated attendance by category
ATTENDANCE_DEFAULTS = {
    'Sports': 5000,
    'Sports - Baseball': 6000,      # Isotopes Park capacity ~13k, avg ~6k
    'Sports - Basketball': 15000,   # The Pit capacity
    'Music': 3000,
    'Festival': 10000,
    'Arts & Culture': 500,
    'Theater': 800,
    'Food & Drink': 1000,
    'Market': 2000,
    'General': 500,
}

print("=" * 70)
print("Populate Estimated Event Times")
print("=" * 70)
print()

print("This will add estimated times to events without time data.")
print("Times are based on typical patterns for each category.")
print()

print("Default Times:")
print("-" * 70)
for category, time in EVENT_TIME_DEFAULTS.items():
    print(f"  {category:20s}: {time}")
print()

proceed = input("Proceed with populating estimated times? (y/n): ").lower()

if proceed != 'y':
    print("Cancelled.")
    exit(0)

print()

conn = get_connection()

try:
    with conn.cursor() as cur:
        # Update times
        updated_times = 0
        
        for category, default_time in EVENT_TIME_DEFAULTS.items():
            cur.execute("""
                UPDATE events
                SET event_time = %s
                WHERE category = %s
                  AND event_time IS NULL
            """, (default_time, category))
            
            count = cur.rowcount
            if count > 0:
                updated_times += count
                logger.info(f"Updated {count} {category} events with {default_time}")
        
        # Update attendance
        updated_attendance = 0
        
        for category, default_attendance in ATTENDANCE_DEFAULTS.items():
            cur.execute("""
                UPDATE events
                SET expected_attendance = %s
                WHERE category = %s
                  AND expected_attendance IS NULL
            """, (default_attendance, category))
            
            count = cur.rowcount
            if count > 0:
                updated_attendance += count
                logger.info(f"Updated {count} {category} events with attendance={default_attendance}")
        
        conn.commit()
        
        print()
        print("=" * 70)
        print("Update Summary")
        print("=" * 70)
        print(f"Events with times added: {updated_times}")
        print(f"Events with attendance added: {updated_attendance}")
        print()
        
        # Verify
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(event_time) as with_time,
                COUNT(expected_attendance) as with_attendance
            FROM events
        """)
        
        total, with_time, with_attendance = cur.fetchone()
        
        print("Current Status:")
        print(f"  Total events: {total}")
        print(f"  Events with time: {with_time} ({with_time*100//total}%)")
        print(f"  Events with attendance: {with_attendance} ({with_attendance*100//total}%)")
        
finally:
    conn.close()

print()
print("=" * 70)
print("✅ Estimated times populated!")
print("=" * 70)
print()
print("Note: These are estimates based on typical patterns.")