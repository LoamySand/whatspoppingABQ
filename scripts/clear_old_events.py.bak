# scripts/clear_old_events.py
"""
Clear old events from database before loading new enhanced data.
Creates backup first for safety.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("Clear Old Events from Database")
print("=" * 70)
print()

print("⚠️  WARNING: This will delete all events from the database!")
print("A backup will be created first.")
print()

proceed = input("Proceed? (yes/no): ").lower()

if proceed != 'yes':
    print("Cancelled.")
    exit(0)

print()

conn = get_connection()

try:
    with conn.cursor() as cur:
        # Create backup
        print("Creating backup...")
        cur.execute("DROP TABLE IF EXISTS events_backup_before_v2")
        cur.execute("CREATE TABLE events_backup_before_v2 AS SELECT * FROM events")
        conn.commit()
        
        cur.execute("SELECT COUNT(*) FROM events_backup_before_v2")
        backup_count = cur.fetchone()[0]
        print(f"✓ Backed up {backup_count} events to events_backup_before_v2")
        print()
        
        # Clear events
        print("Clearing events table...")
        cur.execute("DELETE FROM events")
        conn.commit()
        
        deleted = cur.rowcount
        print(f"✓ Deleted {deleted} events")
        print()
        
        # Verify
        cur.execute("SELECT COUNT(*) FROM events")
        remaining = cur.fetchone()[0]
        print(f"Events remaining: {remaining}")
        
        if remaining == 0:
            print("✓ Database cleared successfully!")
        else:
            print("⚠️  Warning: Some events remain")
        
finally:
    conn.close()

print()
print("=" * 70)
print("To restore from backup if needed:")
print("  INSERT INTO events SELECT * FROM events_backup_before_v2;")
print("=" * 70)