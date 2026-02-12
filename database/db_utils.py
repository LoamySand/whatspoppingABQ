# database/db_utils.py
"""
Database utilities for event analytics pipeline.
Handles connections and data insertion to PostgreSQL.
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Dict, Optional

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
# TODO: Replace 'YOUR_PASSWORD' with your actual PostgreSQL password
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'), 
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}


def get_connection():
    """
    Create and return a database connection.
    
    Returns:
        psycopg2 connection object
        
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.debug("Database connection established")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        conn = get_connection()
        conn.close()
        logger.info("✓ Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"✗ Database connection test failed: {e}")
        return False

def insert_events(events: List[Dict]) -> int:
    """
    Insert events into database with upsert logic.
    
    Deduplicates events before insertion to avoid conflicts.
    Uses ON CONFLICT to update existing events based on
    unique constraint (event_name, event_date).
    
    Args:
        events: List of event dictionaries with keys:
                - event_name (required)
                - venue_name
                - event_date (required)
                - event_time
                - category
                - expected_attendance
                - latitude
                - longitude
                - source_url
    
    Returns:
        Number of events inserted/updated
        
    Raises:
        psycopg2.Error: If database operation fails
    """
    if not events:
        logger.warning("No events to insert")
        return 0
    
    # Deduplicate events based on (event_name, event_date)
    # Keep the first occurrence of each unique event
    seen = set()
    unique_events = []
    duplicates_removed = 0
    
    for event in events:
        key = (event.get('event_name'), event.get('event_date'))
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
        else:
            duplicates_removed += 1
    
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate events from batch")
    
    logger.info(f"Inserting {len(unique_events)} unique events")
    
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            # SQL query with upsert logic
            query = """
                INSERT INTO events 
                (event_name, venue_name, event_date, event_time, 
                 category, expected_attendance, latitude, longitude, source_url)
                VALUES %s
                ON CONFLICT (event_name, event_date) 
                DO UPDATE SET
                    venue_name = EXCLUDED.venue_name,
                    event_time = EXCLUDED.event_time,
                    category = EXCLUDED.category,
                    expected_attendance = EXCLUDED.expected_attendance,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    source_url = EXCLUDED.source_url,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # Prepare values - must match column order in query
            values = [
                (
                    event.get('event_name'),
                    event.get('venue_name'),
                    event.get('event_date'),
                    event.get('event_time'),
                    event.get('category'),
                    event.get('expected_attendance'),
                    event.get('latitude'),
                    event.get('longitude'),
                    event.get('source_url')
                )
                for event in unique_events
            ]
            
            # Execute batch insert
            execute_values(cur, query, values)
            conn.commit()
            
            rows_affected = cur.rowcount
            logger.info(f"Successfully inserted/updated {len(unique_events)} events ({rows_affected} rows affected)")
            return len(unique_events)
            
    except psycopg2.Error as e:
        conn.rollback()
        logger.error(f"Database error during insert: {e}")
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Unexpected error during insert: {e}")
        raise
    finally:
        conn.close()

def get_event_count() -> int:
    """
    Get total count of events in database.
    
    Returns:
        Total number of events
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            count = cur.fetchone()[0]
            return count
    finally:
        conn.close()


def get_recent_events(limit: int = 10) -> List[Dict]:
    """
    Get most recently added/updated events.
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_date, 
                       event_time, category, created_at, updated_at
                FROM events
                ORDER BY updated_at DESC
                LIMIT %s
            """, (limit,))
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                events.append(event)
            
            return events
    finally:
        conn.close()


def get_events_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """
    Get events within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of event dictionaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_date, 
                       event_time, category
                FROM events
                WHERE event_date BETWEEN %s AND %s
                ORDER BY event_date
            """, (start_date, end_date))
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                events.append(event)
            
            return events
    finally:
        conn.close()


def get_events_by_category(category: str) -> List[Dict]:
    """
    Get all events in a specific category.
    
    Args:
        category: Event category (e.g., 'Sports', 'Music', 'Festival')
        
    Returns:
        List of event dictionaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_date, category
                FROM events
                WHERE category = %s
                ORDER BY event_date
            """, (category,))
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                events.append(event)
            
            return events
    finally:
        conn.close()


def get_category_counts() -> Dict[str, int]:
    """
    Get count of events by category.
    
    Returns:
        Dictionary mapping category to count
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM events
                GROUP BY category
                ORDER BY count DESC
            """)
            
            results = {}
            for row in cur.fetchall():
                results[row[0]] = row[1]
            
            return results
    finally:
        conn.close()


def clear_all_events() -> int:
    """
    Delete all events from database.
    
    ⚠️ WARNING: This permanently deletes all event data!
    
    Returns:
        Number of events deleted
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events")
            conn.commit()
            deleted = cur.rowcount
            logger.warning(f"Deleted {deleted} events from database")
            return deleted
    finally:
        conn.close()

# ============================================================
# VENUE LOCATION FUNCTIONS
# ============================================================

def insert_venue(venue_name: str, latitude: float, longitude: float, 
                 address: str = None, place_id: str = None) -> Optional[int]:
    """
    Insert or update a venue location.
    
    Args:
        venue_name: Name of the venue
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        address: Full address (optional)
        place_id: Google Place ID (optional)
        
    Returns:
        venue_id of inserted/updated venue
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Upsert venue
            cur.execute("""
                INSERT INTO venue_locations 
                (venue_name, address, latitude, longitude, place_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (venue_name) 
                DO UPDATE SET
                    address = EXCLUDED.address,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    place_id = EXCLUDED.place_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING venue_id
            """, (venue_name, address, latitude, longitude, place_id))
            
            venue_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"Inserted/updated venue: {venue_name} (ID: {venue_id})")
            return venue_id
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting venue: {e}")
        raise
    finally:
        conn.close()


def get_venue_by_name(venue_name: str) -> Optional[Dict]:
    """
    Get venue information by name.
    
    Args:
        venue_name: Name of the venue
        
    Returns:
        Dictionary with venue info or None
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT venue_id, venue_name, address, latitude, longitude, place_id
                FROM venue_locations
                WHERE venue_name = %s
            """, (venue_name,))
            
            row = cur.fetchone()
            if row:
                return {
                    'venue_id': row[0],
                    'venue_name': row[1],
                    'address': row[2],
                    'latitude': row[3],
                    'longitude': row[4],
                    'place_id': row[5]
                }
            return None
    finally:
        conn.close()


def get_all_venues() -> List[Dict]:
    """
    Get all venues from database.
    
    Returns:
        List of venue dictionaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT venue_id, venue_name, address, latitude, longitude
                FROM venue_locations
                ORDER BY venue_name
            """)
            
            venues = []
            for row in cur.fetchall():
                venues.append({
                    'venue_id': row[0],
                    'venue_name': row[1],
                    'address': row[2],
                    'latitude': row[3],
                    'longitude': row[4]
                })
            return venues
    finally:
        conn.close()


# ============================================================
# TRAFFIC MEASUREMENT FUNCTIONS
# ============================================================

def insert_traffic_measurement(venue_id: int, measurement_time, 
                               traffic_data: Dict) -> int:
    """
    Insert a traffic measurement.
    
    Args:
        venue_id: Venue ID
        measurement_time: When measurement was taken
        traffic_data: Dictionary with traffic metrics
        
    Returns:
        measurement_id of inserted record
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO traffic_measurements (
                    venue_id, measurement_time, traffic_level,
                    avg_speed_mph, typical_speed_mph,
                    travel_time_seconds, typical_time_seconds,
                    delay_minutes, data_source,
                    origin_lat, origin_lng,
                    destination_lat, destination_lng,
                    distance_miles, raw_response
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING measurement_id
            """, (
                venue_id,
                measurement_time,
                traffic_data.get('traffic_level'),
                traffic_data.get('avg_speed_mph'),
                traffic_data.get('typical_speed_mph'),
                traffic_data.get('travel_time_seconds'),
                traffic_data.get('typical_time_seconds'),
                traffic_data.get('delay_minutes'),
                traffic_data.get('data_source', 'google_maps'),
                traffic_data.get('origin_lat'),
                traffic_data.get('origin_lng'),
                traffic_data.get('destination_lat'),
                traffic_data.get('destination_lng'),
                traffic_data.get('distance_miles'),
                traffic_data.get('raw_response')
            ))
            
            measurement_id = cur.fetchone()[0]
            conn.commit()
            
            logger.info(f"Inserted traffic measurement for venue {venue_id}")
            return measurement_id
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting traffic measurement: {e}")
        raise
    finally:
        conn.close()


def get_traffic_for_venue(venue_id: int, limit: int = 100) -> List[Dict]:
    """
    Get recent traffic measurements for a venue.
    
    Args:
        venue_id: Venue ID
        limit: Max number of measurements to return
        
    Returns:
        List of traffic measurement dictionaries
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    measurement_id, measurement_time,
                    traffic_level, delay_minutes,
                    avg_speed_mph, distance_miles
                FROM traffic_measurements
                WHERE venue_id = %s
                ORDER BY measurement_time DESC
                LIMIT %s
            """, (venue_id, limit))
            
            measurements = []
            for row in cur.fetchall():
                measurements.append({
                    'measurement_id': row[0],
                    'measurement_time': row[1],
                    'traffic_level': row[2],
                    'delay_minutes': row[3],
                    'avg_speed_mph': row[4],
                    'distance_miles': row[5]
                })
            return measurements
    finally:
        conn.close()
if __name__ == "__main__":
    """
    Test database utilities when run directly.
    """
    print("=" * 60)
    print("Database Utilities Test")
    print("=" * 60)
    print()
    
    # Test 1: Connection
    print("Test 1: Database Connection")
    print("-" * 60)
    if test_connection():
        print("✓ Connection successful")
    else:
        print("✗ Connection failed - check DB_CONFIG password")
        print("Update the password in db_utils.py and try again")
        exit(1)
    print()
    
    # Test 2: Event count
    print("Test 2: Get Event Count")
    print("-" * 60)
    try:
        count = get_event_count()
        print(f"Total events in database: {count}")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Test 3: Category counts
    print("Test 3: Events by Category")
    print("-" * 60)
    try:
        categories = get_category_counts()
        if categories:
            for category, count in categories.items():
                print(f"  {category}: {count}")
        else:
            print("  No events in database yet")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Test 4: Recent events
    print("Test 4: Recent Events")
    print("-" * 60)
    try:
        recent = get_recent_events(limit=5)
        if recent:
            for i, event in enumerate(recent, 1):
                print(f"{i}. {event['event_name']}")
                print(f"   Date: {event['event_date']} | Category: {event['category']}")
        else:
            print("  No events in database yet")
    except Exception as e:
        print(f"Error: {e}")
    print()
    
    # Test 5: Insert sample event
    print("Test 5: Insert Sample Event")
    print("-" * 60)
    sample_event = {
        'event_name': 'Test Event - Database Utilities',
        'venue_name': 'Test Venue',
        'event_date': '2025-12-31',
        'event_time': None,
        'category': 'Testing',
        'expected_attendance': None,
        'latitude': None,
        'longitude': None,
        'source_url': 'https://test.com'
    }
    
    try:
        result = insert_events([sample_event])
        print(f"✓ Inserted {result} event")
        
        # Verify it was inserted
        new_count = get_event_count()
        print(f"New total: {new_count} events")
    except Exception as e:
        print(f"✗ Error: {e}")
    print()
    
    # Test 6: Upsert (update existing)
    print("Test 6: Test Upsert (Update Existing Event)")
    print("-" * 60)
    sample_event['venue_name'] = 'Updated Test Venue'
    
    try:
        result = insert_events([sample_event])
        print(f"✓ Upserted {result} event")
        
        # Verify count didn't increase
        final_count = get_event_count()
        print(f"Total still: {final_count} events (no duplicate created)")
    except Exception as e:
        print(f"✗ Error: {e}")
    print()
    
    print("=" * 60)
    print("All tests complete!")
    print()
    print("⚠️  Note: Test event 'Test Event - Database Utilities' was added")
    print("   You can delete it manually or run clear_all_events() if needed")
    print("=" * 60)