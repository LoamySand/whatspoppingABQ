"""
Backfill day_of_week and hour_of_day for existing traffic measurements.
Uses PostgreSQL's EXTRACT function to calculate from measurement_time.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection

print("=" * 70)
print("Backfill day_of_week and hour_of_day")
print("=" * 70)
print()

conn = get_connection()

try:
    # Step 1: Check how many records need updating
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) 
            FROM traffic_measurements 
            WHERE day_of_week IS NULL OR hour_of_day IS NULL
        """)
        
        missing_count = cur.fetchone()[0]
        
        print(f"Traffic measurements missing time metadata: {missing_count}")
        print()
        
        if missing_count == 0:
            print(" All traffic measurements already have day_of_week and hour_of_day!")
            exit(0)
    
    # Step 2: Show sample of what will be updated
    print("Sample data to be updated (first 5):")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                measurement_id,
                measurement_time,
                day_of_week,
                hour_of_day,
                EXTRACT(DOW FROM measurement_time) as calculated_dow,
                EXTRACT(HOUR FROM measurement_time) as calculated_hour
            FROM traffic_measurements
            WHERE day_of_week IS NULL OR hour_of_day IS NULL
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            meas_id, meas_time, current_dow, current_hour, calc_dow, calc_hour = row
            print(f"Measurement ID {meas_id}")
            print(f"  Time: {meas_time}")
            print(f"  Current: day_of_week={current_dow}, hour_of_day={current_hour}")
            print(f"  Will set: day_of_week={int(calc_dow)}, hour_of_day={int(calc_hour)}")
            print()
    
    # Step 3: Ask for confirmation
    print("=" * 70)
    response = input(f"Update {missing_count} traffic measurements? (y/n): ")
    print()
    
    if response.lower() != 'y':
        print("Cancelled. No changes made.")
        exit(0)
    
    # Step 4: Update the records
    print("Updating traffic measurements...")
    print("-" * 70)
    
    with conn.cursor() as cur:
        # Use PostgreSQL's EXTRACT to calculate day_of_week and hour_of_day
        cur.execute("""
            UPDATE traffic_measurements
            SET 
                day_of_week = EXTRACT(DOW FROM measurement_time)::INTEGER,
                hour_of_day = EXTRACT(HOUR FROM measurement_time)::INTEGER
            WHERE day_of_week IS NULL OR hour_of_day IS NULL
        """)
        
        updated_count = cur.rowcount
        conn.commit()
    
    print(f" Updated {updated_count} traffic measurements")
    print()
    
    # Step 5: Verify
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) 
            FROM traffic_measurements 
            WHERE day_of_week IS NULL OR hour_of_day IS NULL
        """)
        
        remaining = cur.fetchone()[0]
        
        print("Verification:")
        print(f"  Before: {missing_count} missing metadata")
        print(f"  Updated: {updated_count}")
        print(f"  After: {remaining} missing metadata")
        print()
        
        if remaining > 0:
            print(f" {remaining} measurements still missing metadata")
            print("This might indicate NULL measurement_time values")
            
            # Check for NULL measurement_time
            cur.execute("""
                SELECT COUNT(*) 
                FROM traffic_measurements 
                WHERE measurement_time IS NULL
            """)
            
            null_times = cur.fetchone()[0]
            
            if null_times > 0:
                print(f"  {null_times} measurements have NULL measurement_time")
        else:
            print(" All measurements now have day_of_week and hour_of_day!")
    
    # Step 6: Show distribution
    print()
    print("Distribution by day of week:")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                day_of_week,
                CASE day_of_week
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_name,
                COUNT(*) as count
            FROM traffic_measurements
            WHERE day_of_week IS NOT NULL
            GROUP BY day_of_week
            ORDER BY day_of_week
        """)
        
        for row in cur.fetchall():
            dow, day_name, count = row
            print(f"  {dow} - {day_name:10s}: {count:5d} measurements")
    
    print()
    print("Distribution by hour of day:")
    print("-" * 70)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                hour_of_day,
                COUNT(*) as count
            FROM traffic_measurements
            WHERE hour_of_day IS NOT NULL
            GROUP BY hour_of_day
            ORDER BY hour_of_day
        """)
        
        rows = cur.fetchall()
        
        # Show in a compact format (multiple per line)
        for i in range(0, len(rows), 6):
            line_rows = rows[i:i+6]
            line = "  "
            for hour, count in line_rows:
                line += f"{hour:2d}:00 ({count:4d})  "
            print(line)

finally:
    conn.close()

print()
print("=" * 70)
print("Backfill Complete")
print("=" * 70)