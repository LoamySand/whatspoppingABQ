# scripts/debug_dashboard_data.py
"""
Debug why dashboards aren't showing data
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection

print("=" * 70)
print("Dashboard Data Debug")
print("=" * 70)
print()

conn = get_connection()

try:
    with conn.cursor() as cur:
        # Check events table
        print("1. Events Table:")
        print("-" * 70)
        cur.execute("SELECT COUNT(*) FROM events")
        event_count = cur.fetchone()[0]
        print(f"Total events: {event_count}")
        
        cur.execute("SELECT COUNT(*) FROM events WHERE event_start_time IS NOT NULL")
        with_time = cur.fetchone()[0]
        print(f"Events with time: {with_time}")
        
        cur.execute("SELECT COUNT(*) FROM events WHERE venue_id IS NOT NULL")
        with_venue = cur.fetchone()[0]
        print(f"Events with venue: {with_venue}")
        print()
        
        # Check venue_locations
        print("2. Venue Locations Table:")
        print("-" * 70)
        cur.execute("SELECT COUNT(*) FROM venue_locations")
        venue_count = cur.fetchone()[0]
        print(f"Total venues: {venue_count}")
        print()
        
        # Check traffic_measurements
        print("3. Traffic Measurements Table:")
        print("-" * 70)
        cur.execute("SELECT COUNT(*) FROM traffic_measurements")
        traffic_count = cur.fetchone()[0]
        print(f"Total measurements: {traffic_count}")
        
        cur.execute("SELECT COUNT(*) FROM traffic_measurements WHERE data_source = 'sample_data'")
        sample_count = cur.fetchone()[0]
        print(f"Sample measurements: {sample_count}")
        print()
        
        # Check the view
        print("4. Event Impact Summary View:")
        print("-" * 70)
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM event_impact_summary
            WHERE avg_delay_before IS NOT NULL 
              AND avg_delay_during IS NOT NULL
        """)
        
        view_count = cur.fetchone()[0]
        print(f"Events in impact summary view: {view_count}")
        
        if view_count == 0:
            print()
            print("⚠️  WARNING: No events in event_impact_summary view!")
            print("This is why dashboards are empty.")
            print()
            
            # Check why
            print("Checking why view is empty...")
            print()
            
            # Check for events with venue and time
            cur.execute("""
                SELECT COUNT(*)
                FROM events e
                JOIN venue_locations v ON e.venue_id = v.venue_id
                WHERE e.event_start_time IS NOT NULL
            """)
            events_ready = cur.fetchone()[0]
            print(f"Events with venue and time: {events_ready}")
            
            # Check for traffic in time windows
            cur.execute("""
                SELECT 
                    e.event_name,
                    e.event_start_date,
                    e.event_start_time,
                    COUNT(tm.measurement_id) as traffic_count
                FROM events e
                JOIN venue_locations v ON e.venue_id = v.venue_id
                LEFT JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
                WHERE e.event_start_time IS NOT NULL
                  AND tm.measurement_time BETWEEN 
                      (e.event_start_date + e.event_start_time - INTERVAL '2 hours') AND
                      (e.event_start_date + e.event_start_time + INTERVAL '2 hours')
                GROUP BY e.event_id, e.event_name, e.event_start_date, e.event_start_time
                LIMIT 10
            """)
            
            rows = cur.fetchall()
            
            if rows:
                print()
                print("Events with traffic in ±2 hour window:")
                for row in rows:
                    name, date, time, count = row
                    print(f"  {name[:40]}: {count} measurements")
            else:
                print()
                print("❌ No events have traffic within ±2 hours of event time!")
                print()
                print("Possible causes:")
                print("  1. Traffic measurements have wrong timestamps")
                print("  2. Events and traffic aren't matching up")
                print("  3. Sample data wasn't generated correctly")
        else:
            # Show sample
            print()
            print("Sample events from view:")
            cur.execute("""
                SELECT 
                    event_name,
                    ROUND(avg_delay_before, 2),
                    ROUND(avg_delay_during, 2),
                    ROUND(avg_delay_during - avg_delay_before, 2) as impact
                FROM event_impact_summary
                LIMIT 5
            """)
            
            for row in cur.fetchall():
                name, before, during, impact = row
                print(f"  {name[:40]}: {before} → {during} (+{impact} min)")

finally:
    conn.close()

print()
print("=" * 70)