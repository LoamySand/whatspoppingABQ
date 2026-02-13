# analysis/event_traffic_correlation.py
"""
Analyze correlation between events and traffic patterns.
Quantify event impact on local traffic.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import get_connection
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_traffic_for_event(event_id: int) -> Dict:
    """
    Get all traffic measurements associated with an event.
    
    Args:
        event_id: Event ID
        
    Returns:
        Dictionary with event info and traffic measurements
    """
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            # Get event details
            cur.execute("""
                SELECT 
                    e.event_id,
                    e.event_name,
                    e.event_start_date,
                    e.event_start_time,
                    e.category,
                    e.is_multi_day,
                    v.venue_id,
                    v.venue_name,
                    v.latitude,
                    v.longitude
                FROM events e
                JOIN venue_locations v ON e.venue_id = v.venue_id
                WHERE e.event_id = %s
            """, (event_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            event = {
                'event_id': row[0],
                'event_name': row[1],
                'event_start_date': row[2],
                'event_start_time': row[3],
                'category': row[4],
                'is_multi_day': row[5],
                'venue_id': row[6],
                'venue_name': row[7],
                'latitude': row[8],
                'longitude': row[9]
            }
            
            # Get event datetime
            event_datetime = datetime.combine(
                event['event_start_date'],
                event['event_start_time'] or datetime.min.time()
            )
            
            # Get traffic measurements within event window (2 hours before to 2 hours after)
            cur.execute("""
                SELECT 
                    measurement_id,
                    measurement_time,
                    traffic_level,
                    avg_speed_mph,
                    typical_speed_mph,
                    delay_minutes,
                    distance_miles
                FROM traffic_measurements
                WHERE venue_id = %s
                  AND measurement_time BETWEEN %s AND %s
                ORDER BY measurement_time
            """, (
                event['venue_id'],
                event_datetime - timedelta(hours=2),
                event_datetime + timedelta(hours=2)
            ))
            
            measurements = []
            for row in cur.fetchall():
                measurements.append({
                    'measurement_id': row[0],
                    'measurement_time': row[1],
                    'traffic_level': row[2],
                    'avg_speed_mph': row[3],
                    'typical_speed_mph': row[4],
                    'delay_minutes': row[5],
                    'distance_miles': row[6]
                })
            
            event['traffic_measurements'] = measurements
            event['event_datetime'] = event_datetime
            
            return event
            
    finally:
        conn.close()


def analyze_event_impact(event: Dict) -> Dict:
    """
    Analyze traffic impact of a specific event.
    
    Args:
        event: Event dictionary with traffic measurements
        
    Returns:
        Dictionary with impact analysis
    """
    measurements = event.get('traffic_measurements', [])
    
    if not measurements:
        return {
            'has_data': False,
            'reason': 'No traffic measurements available'
        }
    
    # Sort measurements by time and split into first half (before) and second half (during/after)
    measurements = sorted(measurements, key=lambda m: m['measurement_time'])
    mid_point = len(measurements) // 2
    before_measurements = measurements[:mid_point]
    during_measurements = measurements[mid_point:]
    
    # Calculate statistics
    def calc_stats(measurements_list):
        if not measurements_list:
            return None
        
        delays = [m['delay_minutes'] for m in measurements_list if m['delay_minutes'] is not None]
        speeds = [m['avg_speed_mph'] for m in measurements_list if m['avg_speed_mph'] is not None]
        
        return {
            'count': len(measurements_list),
            'avg_delay': sum(delays) / len(delays) if delays else None,
            'max_delay': max(delays) if delays else None,
            'avg_speed': sum(speeds) / len(speeds) if speeds else None,
            'traffic_levels': [m['traffic_level'] for m in measurements_list]
        }
    
    before_stats = calc_stats(before_measurements)
    during_stats = calc_stats(during_measurements)
    
    # Calculate impact (before vs during)
    impact = {}
    
    if before_stats and during_stats:
        if before_stats['avg_delay'] is not None and during_stats['avg_delay'] is not None:
            impact['delay_increase'] = during_stats['avg_delay'] - before_stats['avg_delay']
            impact['delay_increase_pct'] = (
                (during_stats['avg_delay'] - before_stats['avg_delay']) / 
                (abs(before_stats['avg_delay']) + 1) * 100  # +1 to avoid division by zero
            )
        
        if before_stats['avg_speed'] is not None and during_stats['avg_speed'] is not None:
            impact['speed_decrease'] = before_stats['avg_speed'] - during_stats['avg_speed']
            impact['speed_decrease_pct'] = (
                (before_stats['avg_speed'] - during_stats['avg_speed']) / 
                before_stats['avg_speed'] * 100
            )
    
    # Determine impact level
    if impact.get('delay_increase') is not None:
        # We have valid data to classify
        delay_increase = impact['delay_increase']
        if delay_increase == 0:
            impact['level'] = 'no impact'
        elif delay_increase > 5:
            impact['level'] = 'severe'
        elif delay_increase > 2:
            impact['level'] = 'high'
        elif delay_increase > 1:
            impact['level'] = 'moderate'
        elif delay_increase > 0:
            impact['level'] = 'low'
        else:
            impact['level'] = 'no impact'
    else:
        impact['level'] = 'unknown'
    
    return {
        'has_data': True,
        'event_id': event['event_id'],
        'event_name': event['event_name'],
        'category': event['category'],
        'venue_name': event['venue_name'],
        'before': before_stats,
        'during': during_stats,
        'impact': impact,
        'total_measurements': len(measurements)
    }


def get_events_with_traffic_data(limit: int = None) -> List[int]:
    """
    Get event IDs that have associated traffic measurements.
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        List of event IDs
    """
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            query = """
                SELECT DISTINCT e.event_id, e.event_start_date
                FROM events e
                JOIN traffic_measurements tm ON e.venue_id = tm.venue_id
                WHERE e.event_start_time IS NOT NULL
                  AND tm.measurement_time BETWEEN 
                      (e.event_start_date + e.event_start_time - INTERVAL '2 hours') AND
                      (e.event_start_date + e.event_start_time + INTERVAL '2 hours')
                ORDER BY e.event_start_date DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            
            return [row[0] for row in cur.fetchall()]
            
    finally:
        conn.close()


def analyze_all_events() -> List[Dict]:
    """
    Analyze traffic impact for all events with data.
    
    Returns:
        List of analysis dictionaries
    """
    logger.info("Analyzing all events with traffic data")
    
    event_ids = get_events_with_traffic_data()
    
    logger.info(f"Found {len(event_ids)} events with traffic data")
    
    results = []
    
    for event_id in event_ids:
        event = get_traffic_for_event(event_id)
        if event:
            analysis = analyze_event_impact(event)
            if analysis.get('has_data'):
                results.append(analysis)
    
    logger.info(f"Analyzed {len(results)} events")
    
    return results


def get_impact_summary(analyses: List[Dict]) -> Dict:
    """
    Generate summary statistics from event analyses.
    
    Args:
        analyses: List of analysis dictionaries
        
    Returns:
        Summary statistics dictionary
    """
    if not analyses:
        return {'no_data': True}
    
    # Overall statistics
    total_events = len(analyses)
    
    # Impact levels
    impact_levels = {}
    for analysis in analyses:
        level = analysis['impact'].get('level', 'unknown')
        impact_levels[level] = impact_levels.get(level, 0) + 1
    
    # Category breakdown
    category_impacts = {}
    for analysis in analyses:
        cat = analysis['category']
        if cat not in category_impacts:
            category_impacts[cat] = []
        
        delay_increase = analysis['impact'].get('delay_increase')
        if delay_increase is not None:
            category_impacts[cat].append(delay_increase)
    
    category_avg = {
        cat: sum(delays) / len(delays) if delays else 0
        for cat, delays in category_impacts.items()
    }
    
    # Top events by impact
    events_with_impact = [
        a for a in analyses 
        if a['impact'].get('delay_increase') is not None
    ]
    
    top_events = sorted(
        events_with_impact,
        key=lambda x: x['impact']['delay_increase'],
        reverse=True
    )[:10]
    
    return {
        'total_events_analyzed': total_events,
        'impact_levels': impact_levels,
        'category_avg_impact': category_avg,
        'top_impact_events': [
            {
                'event_name': e['event_name'],
                'category': e['category'],
                'venue': e['venue_name'],
                'delay_increase': e['impact']['delay_increase'],
                'impact_level': e['impact']['level']
            }
            for e in top_events
        ]
    }


if __name__ == "__main__":
    """
    Test correlation analysis
    """
    print("=" * 70)
    print("Event-Traffic Correlation Analysis")
    print("=" * 70)
    print()
    
    # Analyze all events
    analyses = analyze_all_events()
    
    if not analyses:
        print("No events with traffic data found!")
        print()
        print("Make sure you have:")
        print("  1. Events in the database with times")
        print("  2. Traffic measurements collected")
        exit(0)
    
    # Generate summary
    summary = get_impact_summary(analyses)
    
    print(f"Total events analyzed: {summary['total_events_analyzed']}")
    print()
    
    print("Impact Levels:")
    print("-" * 70)
    impact_order = {'severe': 0, 'high': 1, 'moderate': 2, 'low': 3, 'no impact': 4}
    for level, count in sorted(summary['impact_levels'].items(), key=lambda x: impact_order.get(x[0], 999)):
        pct = count * 100 / summary['total_events_analyzed']
        print(f"  {level:10s}: {count:3d} ({pct:5.1f}%)")
    print()
    
    print("Average Impact by Category:")
    print("-" * 70)
    for cat, avg_delay in sorted(
        summary['category_avg_impact'].items(),
        key=lambda x: x[1],
        reverse=True
    ):
        print(f"  {cat:30s}: {avg_delay:6.2f} min delay")
    print()
    
    print("Top 5 Events by Traffic Impact:")
    print("-" * 70)
    for i, event in enumerate(summary['top_impact_events'][:5], 1):
        print(f"{i}. {event['event_name']}")
        print(f"   Category: {event['category']}")
        print(f"   Venue: {event['venue']}")
        print(f"   Impact: +{event['delay_increase']:.1f} min delay ({event['impact_level']})")
        print()
    
    print("=" * 70)