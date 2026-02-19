# database/db_utils.py
"""
Database utilities for event analytics pipeline.
Handles connections and data insertion to PostgreSQL.
Supports both local .env and Streamlit Cloud secrets with Supabase pooler.
"""
import datetime
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import logging
from typing import List, Dict, Optional

# Load environment variables from .env file
# Find the project root (.env location) relative to this file
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=env_path, override=True)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_connection():
    """
    Get database connection.
    Supports both local .env and Streamlit Cloud secrets.
    Creates a NEW connection each time (important for pooler).
    
    Returns:
        psycopg2 connection object
        
    Raises:
        psycopg2.Error: If connection fails
    """
    
    # Ensure .env is loaded fresh (important for subprocesses)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    
    # Try Streamlit secrets first (for deployed app)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'DB_HOST' in st.secrets:
            logger.debug("Using Streamlit secrets for connection")
            return psycopg2.connect(
                host=st.secrets["DB_HOST"],
                port=int(st.secrets.get("DB_PORT", 6543)),
                database=st.secrets["DB_NAME"],
                user=st.secrets["DB_USER"],
                password=st.secrets["DB_PASSWORD"],
                sslmode='require',
                connect_timeout=10
            )
    except (ImportError, AttributeError, FileNotFoundError, KeyError):
        # Streamlit not available or no secrets, use .env
        pass
    
    # Fallback to .env (for local development)
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', '5432'))
    database = os.getenv('DB_NAME', 'postgres')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD')
    
    # DEBUG: Log connection details
    logger.info(f"[CONNECTION] Host: {host}")
    logger.info(f"[CONNECTION] Port: {port}")
    logger.info(f"[CONNECTION] Database: {database}")
    logger.info(f"[CONNECTION] User: {user}")
    
    # Determine if using Supabase
    is_supabase = 'supabase' in host
    
    conn_params = {
        'host': host,
        'port': port,
        'database': database,
        'user': user,
        'password': password,
        'connect_timeout': 10
    }
    
    # Add SSL for Supabase
    if is_supabase:
        conn_params['sslmode'] = 'require'
    
    try:
        conn = psycopg2.connect(**conn_params)
        logger.debug("Database connection established")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def query_to_dataframe(query: str):
    """
    Execute query and return DataFrame.
    Creates and closes connection for each query (important for pooler).
    
    Args:
        query: SQL query string
        
    Returns:
        pandas DataFrame
    """
    import pandas as pd
    
    conn = None
    try:
        conn = get_connection()
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        logger.error(f"Database query error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if conn and not conn.closed:
            conn.close()


def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        conn = get_connection()
        conn.close()
        logger.info(" Database connection test successful")
        return True
    except Exception as e:
        logger.error(f" Database connection test failed: {e}")
        return False

def insert_events(events: List[Dict]) -> int:
    """
    Insert events into database with upsert logic.
    
    Uses new schema with start/end dates and times.
    
    Deduplicates events before insertion to avoid conflicts.
    Uses ON CONFLICT to update existing events based on
    unique constraint (event_name, event_start_date, venue_name).
    
    Args:
        events: List of event dictionaries
    
    Returns:
        Number of events inserted/updated
        
    Raises:
        psycopg2.Error: If database operation fails
    """
    if not events:
        logger.warning("No events to insert")
        return 0
    
    # Deduplicate events based on (event_name, event_start_date, venue_name)
    seen = set()
    unique_events = []
    duplicates_removed = 0
    
    for event in events:
        key = (
            event.get('event_name'), 
            event.get('event_start_date'),
            event.get('venue_name')
        )
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
        else:
            duplicates_removed += 1
    
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate events from batch")
    
    logger.info(f"Inserting {len(unique_events)} unique events")
    
    conn = None
    
    try:
        conn = get_connection()
        
        with conn.cursor() as cur:
            # SQL query with upsert logic
            query = """
                INSERT INTO events 
                (event_name, venue_name, 
                 event_start_date, event_end_date, 
                 event_start_time, event_end_time,
                 is_multi_day,
                 category, 
                 sponsor,
                 cost_min, cost_max, cost_description,
                 phone, email,
                 ticket_url, website_url,
                 expected_attendance, 
                 latitude, longitude, 
                 source_url)
                VALUES %s
                ON CONFLICT (event_name, event_start_date, venue_name) 
                DO UPDATE SET
                    event_end_date = EXCLUDED.event_end_date,
                    event_start_time = EXCLUDED.event_start_time,
                    event_end_time = EXCLUDED.event_end_time,
                    is_multi_day = EXCLUDED.is_multi_day,
                    category = EXCLUDED.category,
                    sponsor = EXCLUDED.sponsor,
                    cost_min = EXCLUDED.cost_min,
                    cost_max = EXCLUDED.cost_max,
                    cost_description = EXCLUDED.cost_description,
                    phone = EXCLUDED.phone,
                    email = EXCLUDED.email,
                    ticket_url = EXCLUDED.ticket_url,
                    website_url = EXCLUDED.website_url,
                    expected_attendance = EXCLUDED.expected_attendance,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    source_url = EXCLUDED.source_url,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            # Prepare values
            values = [
                (
                    event.get('event_name'),
                    event.get('venue_name'),
                    event.get('event_start_date'),
                    event.get('event_end_date'),
                    event.get('event_start_time'),
                    event.get('event_end_time'),
                    event.get('is_multi_day', False),
                    event.get('category'),
                    event.get('sponsor'),
                    event.get('cost_min'),
                    event.get('cost_max'),
                    event.get('cost_description'),
                    event.get('phone'),
                    event.get('email'),
                    event.get('ticket_url'),
                    event.get('website_url'),
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
        if conn:
            conn.rollback()
        logger.error(f"Database error during insert: {e}")
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error during insert: {e}")
        raise
    finally:
        if conn and not conn.closed:
            conn.close()

def get_event_count() -> int:
    """Get total count of events in database."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            count = cur.fetchone()[0]
            return count
    finally:
        if conn and not conn.closed:
            conn.close()


def get_recent_events(limit: int = 10) -> List[Dict]:
    """Get most recently added/updated events."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_start_date, 
                       event_start_time, category, created_at, updated_at
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
        if conn and not conn.closed:
            conn.close()


def get_events_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """Get events within a date range."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_start_date, 
                       event_start_time, category
                FROM events
                WHERE event_start_date BETWEEN %s AND %s
                ORDER BY event_start_date
            """, (start_date, end_date))
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                events.append(event)
            
            return events
    finally:
        if conn and not conn.closed:
            conn.close()


def get_events_by_category(category: str) -> List[Dict]:
    """Get all events in a specific category."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_start_date, category
                FROM events
                WHERE category = %s
                ORDER BY event_start_date
            """, (category,))
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                events.append(event)
            
            return events
    finally:
        if conn and not conn.closed:
            conn.close()


def get_category_counts() -> Dict[str, int]:
    """Get count of events by category."""
    conn = None
    try:
        conn = get_connection()
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
        if conn and not conn.closed:
            conn.close()


def get_event_statistics() -> Dict:
    """Get comprehensive statistics about events in database."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Total events
            cur.execute("SELECT COUNT(*) FROM events")
            total_events = cur.fetchone()[0]
            
            # Multi-day events
            cur.execute("SELECT COUNT(*) FROM events WHERE is_multi_day = true")
            multi_day_count = cur.fetchone()[0]
            
            # Events by category
            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM events
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)
            category_counts = {row[0]: row[1] for row in cur.fetchall()}
            
            # Events by venue
            cur.execute("""
                SELECT venue_name, COUNT(*) as count
                FROM events
                WHERE venue_name IS NOT NULL
                GROUP BY venue_name
                ORDER BY count DESC
                LIMIT 10
            """)
            top_venues = {row[0]: row[1] for row in cur.fetchall()}
            
            return {
                'total_events': total_events,
                'multi_day_events': multi_day_count,
                'by_category': category_counts,
                'top_venues': top_venues
            }
    finally:
        if conn and not conn.closed:
            conn.close()


def get_multi_day_events() -> List[Dict]:
    """Get all multi-day events."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, event_name, venue_name, event_start_date, 
                       event_end_date, category
                FROM events
                WHERE is_multi_day = true
                ORDER BY event_start_date DESC
            """)
            
            columns = [desc[0] for desc in cur.description]
            events = []
            for row in cur.fetchall():
                events.append(dict(zip(columns, row)))
            
            return events
    finally:
        if conn and not conn.closed:
            conn.close()


def clear_all_events() -> int:
    """Delete all events from database. WARNING: Permanent!"""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events")
            conn.commit()
            deleted = cur.rowcount
            logger.warning(f"Deleted {deleted} events from database")
            return deleted
    finally:
        if conn and not conn.closed:
            conn.close()

# ============================================================
# VENUE LOCATION FUNCTIONS
# ============================================================

def insert_venue(venue_name: str, latitude: float, longitude: float, 
                 address: str = None, place_id: str = None) -> Optional[int]:
    """Insert or update a venue location."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
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
        if conn:
            conn.rollback()
        logger.error(f"Error inserting venue: {e}")
        raise
    finally:
        if conn and not conn.closed:
            conn.close()


def get_venue_by_name(venue_name: str) -> Optional[Dict]:
    """Get venue information by name."""
    conn = None
    try:
        conn = get_connection()
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
        if conn and not conn.closed:
            conn.close()


def get_all_venues() -> List[Dict]:
    """Get all venues from database."""
    conn = None
    try:
        conn = get_connection()
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
        if conn and not conn.closed:
            conn.close()


# ============================================================
# TRAFFIC MEASUREMENT FUNCTIONS
# ============================================================
def insert_traffic_measurement(venue_id: int, measurement_time: datetime, 
                               traffic_data: Dict, event_id: int = None) -> int:
    """Insert a traffic measurement into the database."""
    conn = None
    
    try:
        conn = get_connection()
        
        with conn.cursor() as cur:
            # Calculate metadata
            day_of_week = (measurement_time.weekday() + 1) % 7  # 0=Sun, 6=Sat
            hour_of_day = measurement_time.hour
            
            # Determine if baseline
            is_baseline = traffic_data.get('is_baseline', False)
            baseline_type = traffic_data.get('baseline_type') if is_baseline else None
            
            query = """
                INSERT INTO traffic_measurements (
                    venue_id, event_id, measurement_time, traffic_level,
                    avg_speed_mph, typical_speed_mph, travel_time_seconds,
                    typical_time_seconds, delay_minutes, origin_lat, origin_lng,
                    destination_lat, destination_lng, distance_miles, data_source,
                    raw_response, is_baseline, baseline_type, day_of_week, hour_of_day
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING measurement_id
            """
            
            cur.execute(query, (
                venue_id, event_id, measurement_time,
                traffic_data.get('traffic_level'),
                traffic_data.get('avg_speed_mph'),
                traffic_data.get('typical_speed_mph'),
                traffic_data.get('travel_time_seconds'),
                traffic_data.get('typical_time_seconds'),
                traffic_data.get('delay_minutes'),
                traffic_data.get('origin_lat'),
                traffic_data.get('origin_lng'),
                traffic_data.get('destination_lat'),
                traffic_data.get('destination_lng'),
                traffic_data.get('distance_miles'),
                traffic_data.get('data_source', 'tomtom'),
                traffic_data.get('raw_response'),
                is_baseline, baseline_type,
                day_of_week, hour_of_day
            ))
            
            measurement_id = cur.fetchone()[0]
            conn.commit()
            
            return measurement_id
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error inserting traffic measurement: {e}")
        raise
    finally:
        if conn and not conn.closed:
            conn.close()


def get_traffic_for_venue(venue_id: int, limit: int = 100) -> List[Dict]:
    """Get recent traffic measurements for a venue."""
    conn = None
    try:
        conn = get_connection()
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
        if conn and not conn.closed:
            conn.close()


# Additional helper functions (truncated for brevity - keep the rest as-is)
# Just make sure ALL functions close connections in finally blocks

if __name__ == "__main__":
    """Test database utilities when run directly."""
    print("=" * 60)
    print("Database Utilities Test")
    print("=" * 60)
    print()
    
    # Test 1: Connection
    print("Test 1: Database Connection")
    print("-" * 60)
    if test_connection():
        print(" Connection successful")
    else:
        print(" Connection failed")
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
    
    print("=" * 60)
    print("All tests complete!")