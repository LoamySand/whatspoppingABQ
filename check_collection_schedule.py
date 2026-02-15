# scripts/check_collection_schedule.py
"""
Check what should be collecting today and estimate API usage.
Run this daily to track API call usage.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from datetime import datetime, timedelta
from database.db_utils import get_connection

now = datetime.now()
day = now.day
hour = now.hour
minute = now.minute

print("=" * 70)
print(f"Collection Schedule & API Usage Report")
print(f"{now.strftime('%A, %B %d, %Y - %H:%M')}")
print("=" * 70)
print()

# ============================================================
# BASELINE COLLECTION STATUS
# ============================================================
print("BASELINE COLLECTION (TomTom API)")
print("-" * 70)

conn = get_connection()

try:
    with conn.cursor() as cur:
        # Get total venues
        cur.execute("SELECT COUNT(*) FROM venue_locations")
        total_venues = cur.fetchone()[0]
        
        group_size = total_venues // 2

finally:
    conn.close()

if 8 <= day <= 14:
    print(" ACTIVE - Week 2 (Group 1)")
    print(f"  Venues: ~{group_size} (first half of {total_venues} total)")
    baseline_active = True
    baseline_group = 1
elif 22 <= day <= 30:
    print(" ACTIVE - Week 4 (Group 2)")
    print(f"  Venues: ~{group_size} (second half of {total_venues} total)")
    baseline_active = True
    baseline_group = 2
else:
    print("○ INACTIVE (Week 1 or Week 3)")
    print(f"  Next collection: ", end="")
    if day < 8:
        print(f"Week 4 (day 22) of this month")
    else:
        print(f"Week 2 of next month")
    baseline_active = False
    baseline_group = None

print()

if baseline_active:
    print("Collection times today:")
    times = ["07:00", "12:00", "17:00", "19:00", "21:00", "23:00"]
    completed_collections = 0
    upcoming_collections = 0
    
    for t in times:
        t_hour, t_minute = map(int, t.split(':'))
        
        if t_hour < hour or (t_hour == hour and t_minute <= minute):
            status = " Completed"
            completed_collections += 1
        elif t_hour == hour:
            status = "→ COLLECTING NOW"
        else:
            status = "○ Upcoming"
            upcoming_collections += 1
        
        print(f"  {status:15s} {t}")
    
    print()
    print(f"Today's baseline API usage:")
    calls_per_slot = group_size * 4  # 4 directions per venue
    total_today = calls_per_slot * 6
    completed_calls = calls_per_slot * completed_collections
    remaining_calls = calls_per_slot * upcoming_collections
    
    print(f"  Completed: {completed_calls:,} calls ({completed_collections}/6 time slots)")
    print(f"  Remaining: {remaining_calls:,} calls ({upcoming_collections}/6 time slots)")
    print(f"  Total today: {total_today:,} calls")
    print(f"  Daily limit: 2,500 calls (TomTom free tier)")
    print(f"  Usage: {total_today/2500*100:.1f}% of daily limit")

print()
print()

# ============================================================
# EVENT COLLECTION STATUS
# ============================================================
print("EVENT COLLECTION (Google Maps API)")
print("-" * 70)

conn = get_connection()

try:
    with conn.cursor() as cur:
        # Get events today with times
        cur.execute("""
            SELECT 
                e.event_id,
                e.event_name,
                e.event_start_time,
                e.category,
                v.venue_name
            FROM events e
            JOIN venue_locations v ON e.venue_id = v.venue_id
            WHERE e.event_start_date = CURRENT_DATE
              AND e.event_start_time IS NOT NULL
            ORDER BY e.event_start_time
        """)
        
        events_today = []
        for row in cur.fetchall():
            events_today.append({
                'event_id': row[0],
                'event_name': row[1],
                'event_start_time': row[2],
                'category': row[3],
                'venue_name': row[4]
            })

finally:
    conn.close()

if not events_today:
    print("○ No events with scheduled times today")
    print("  Event collection will not run")
    print()
    print("API usage today: 0 calls")
else:
    print(f" {len(events_today)} event(s) with scheduled times today")
    print()
    
    total_event_calls = 0
    
    for i, event in enumerate(events_today, 1):
        event_time = event['event_start_time']
        event_datetime = datetime.combine(now.date(), event_time)
        
        print(f"Event {i}: {event['event_name'][:50]}")
        print(f"  Time: {event_time.strftime('%H:%M')}")
        print(f"  Venue: {event['venue_name'][:40]}")
        print(f"  Category: {event['category']}")
        print()
        
        # Calculate collection windows (every 30 min from -1hr to +1hr)
        collection_points = []
        
        for offset_minutes in range(-60, 61, 30):
            collection_time = event_datetime + timedelta(minutes=offset_minutes)
            
            # Determine status
            if collection_time < now:
                if (now - collection_time) < timedelta(minutes=30):
                    status = "→ Collecting now"
                else:
                    status = " Completed"
            else:
                status = "○ Upcoming"
            
            window_label = ""
            if offset_minutes < -15:
                window_label = "before"
            elif offset_minutes > 15:
                window_label = "after"
            else:
                window_label = "during"
            
            collection_points.append({
                'time': collection_time,
                'offset': offset_minutes,
                'status': status,
                'window': window_label
            })
        
        print(f"  Collection schedule (5 time points, 2 directions each = 10 calls):")
        
        completed = 0
        upcoming = 0
        
        for point in collection_points:
            print(f"    {point['status']:15s} {point['time'].strftime('%H:%M')} ({point['offset']:+4d} min, {point['window']})")
            
            if "Completed" in point['status']:
                completed += 1
            elif "Upcoming" in point['status']:
                upcoming += 1
        
        calls_this_event = 10  # 5 points × 2 directions
        completed_calls = (completed / 5) * calls_this_event
        remaining_calls = (upcoming / 5) * calls_this_event
        
        print()
        print(f"  API calls: {completed_calls:.0f} completed, {remaining_calls:.0f} remaining ({calls_this_event} total)")
        print()
        
        total_event_calls += calls_this_event
    
    print("-" * 70)
    print(f"Total event API usage today: {total_event_calls} calls (Google Maps)")
    print(f"Monthly free tier: 10k calls (~322 a day)")
    print(f"Cost today: ${total_event_calls * 0.007:.2f}")

print()
print()

# ============================================================
# OVERALL SUMMARY
# ============================================================
print("TODAY'S API USAGE SUMMARY")
print("=" * 70)

baseline_calls_today = 0
if baseline_active:
    baseline_calls_today = group_size * 4 * 6

event_calls_today = len(events_today) * 10 if events_today else 0

print(f"Baseline (TomTom):     {baseline_calls_today:5,} calls")
print(f"Events (Google Maps):  {event_calls_today:5,} calls")
print(f"{'':20s}  {'─'*11}")
print(f"Total:                 {baseline_calls_today + event_calls_today:5,} calls")
print()

if baseline_active:
    print(f"TomTom daily limit:    2,500 calls (free tier)")
    print(f"TomTom usage today:    {baseline_calls_today/2500*100:5.1f}%")
    print()

print(f"Google Maps calls today: {event_calls_today}")
print(f"Google Maps monthly:    ~{event_calls_today * 30:.2f} (if similar daily)")

print()
print("=" * 70)

# ============================================================
# HISTORICAL USAGE
# ============================================================
print()
print("HISTORICAL API USAGE (Last 7 Days)")
print("-" * 70)

conn = get_connection()

try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                DATE(measurement_time) as date,
                data_source,
                COUNT(*) as calls
            FROM traffic_measurements
            WHERE measurement_time >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(measurement_time), data_source
            ORDER BY date DESC, data_source
        """)
        
        usage_by_day = {}
        for row in cur.fetchall():
            date, source, calls = row
            if date not in usage_by_day:
                usage_by_day[date] = {'google_maps': 0, 'tomtom': 0}
            usage_by_day[date][source] = calls
        
        if usage_by_day:
            print(f"{'Date':<12} {'Google Maps':>12} {'TomTom':>12}")
            print("-" * 70)
            
            total_google = 0
            total_tomtom = 0
            
            for date in sorted(usage_by_day.keys(), reverse=True):
                google = usage_by_day[date].get('google_maps', 0)
                tomtom = usage_by_day[date].get('tomtom', 0)
                total = google + tomtom
                cost = google * 0.007
                
                total_google += google
                total_tomtom += tomtom
                
                print(f"{str(date):<12} {google:>12,} {tomtom:>12,}")
            
            print("-" * 70)
            print(f"{'7-day total':<12} {total_google:>12,} {total_tomtom:>12,}")
            print()
            print(f"7-day average: {(total_google + total_tomtom)/7:.0f} calls/day")
        else:
            print("No historical data available")

finally:
    conn.close()

print()
print("=" * 70)