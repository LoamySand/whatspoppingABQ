"""
Check what should be collecting today
"""

from datetime import datetime

now = datetime.now()
day = now.day
hour = now.hour

print("=" * 70)
print(f"Collection Schedule Check - {now.strftime('%Y-%m-%d %H:%M')}")
print("=" * 70)
print()

# Baseline collection
if 1 <= day <= 7:
    print("✓ BASELINE COLLECTION ACTIVE - Week 1 (Group 1)")
    print(f"  Collecting for ~40 venues (first half)")
elif 15 <= day <= 21:
    print("✓ BASELINE COLLECTION ACTIVE - Week 3 (Group 2)")
    print(f"  Collecting for ~40 venues (second half)")
else:
    print("○ Baseline collection inactive (Week 2 or Week 4)")

print()
print("Baseline collection times today:")
times = ["07:00", "12:00", "17:00", "19:00", "21:00", "23:00"]
for t in times:
    t_hour = int(t.split(':')[0])
    if t_hour == hour:
        print(f"  → {t} ← CURRENT HOUR")
    elif t_hour > hour:
        print(f"    {t} (upcoming)")
    else:
        print(f"    {t} (completed)")

print()
print("Enhanced event collection:")
print("  Runs every 30 minutes (24/7)")
print(f"  Next run: Top or bottom of the hour")

print()
print("=" * 70)