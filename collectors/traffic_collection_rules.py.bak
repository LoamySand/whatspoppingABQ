"""
Rules for traffic data collection based on event characteristics.
"""

# Major event categories (collect before + after)
MAJOR_CATEGORIES = [
    'Sports',
    'Sports/Fitness', 
    'Festival',
    'Festivals & Special Events',
    'Music',
    'Concerts & Music'
]

# Minor event categories (collect before only)
MINOR_CATEGORIES = [
    'General',
    'Arts & Culture',
    'Theater',
    'Food & Drink',
    'Food, Wine & Beer'
]

# Collection rules
COLLECTION_RULES = {
    'major_events': {
        'categories': MAJOR_CATEGORIES,
        'collect_before': True,
        'collect_after': True,
        'hours_before': 1,
        'hours_after': 1,
        'num_directions': 4,
        'directions': ['North', 'South', 'East', 'West']
    },
    'minor_events': {
        'categories': MINOR_CATEGORIES,
        'collect_before': True,
        'collect_after': False,
        'hours_before': 1,
        'num_directions': 2,
        'directions': ['North', 'South']
    },
    'multi_day': {
        'collect_first_day_only': True,
        'treat_as': 'major_events'  # Use major event rules for first day
    },
    'no_time': {
        'skip': True  # Skip events without times
    }
}


def is_major_event(category: str) -> bool:
    """Check if event is major based on category."""
    return any(cat.lower() in category.lower() for cat in MAJOR_CATEGORIES)


def get_collection_plan(event: dict) -> dict:
    """
    Determine collection plan for an event.
    
    Args:
        event: Event dictionary with category, is_multi_day, event_start_time
        
    Returns:
        Dictionary with collection plan
    """
    # Skip if no time
    if not event.get('event_start_time'):
        return {
            'collect': False,
            'reason': 'No event time available'
        }
    
    # Determine if major or minor
    is_major = is_major_event(event.get('category', ''))
    
    # Multi-day events - collect on first day only
    if event.get('is_multi_day'):
        if is_major:
            return {
                'collect': True,
                'type': 'major_multi_day',
                'collect_before': True,
                'collect_after': True,
                'hours_before': 1,
                'hours_after': 1,
                'num_directions': 4,
                'directions': ['North', 'South', 'East', 'West'],
                'estimated_calls': 8  # 4 before + 4 after
            }
        else:
            return {
                'collect': True,
                'type': 'minor_multi_day',
                'collect_before': True,
                'collect_after': False,
                'hours_before': 1,
                'num_directions': 2,
                'directions': ['North', 'South'],
                'estimated_calls': 2  # 2 before only
            }
    
    # Single-day events
    if is_major:
        return {
            'collect': True,
            'type': 'major_single_day',
            'collect_before': True,
            'collect_after': True,
            'hours_before': 1,
            'hours_after': 1,
            'num_directions': 4,
            'directions': ['North', 'South', 'East', 'West'],
            'estimated_calls': 8  # 4 before + 4 after
        }
    else:
        return {
            'collect': True,
            'type': 'minor_single_day',
            'collect_before': True,
            'collect_after': False,
            'hours_before': 1,
            'num_directions': 2,
            'directions': ['North', 'South'],
            'estimated_calls': 2  # 2 before only
        }


def estimate_monthly_api_calls(events: list) -> dict:
    """
    Estimate monthly API calls for a list of events.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Dictionary with call estimates
    """
    total_calls = 0
    by_type = {}
    skipped = 0
    
    for event in events:
        plan = get_collection_plan(event)
        
        if plan['collect']:
            event_type = plan['type']
            calls = plan['estimated_calls']
            
            total_calls += calls
            by_type[event_type] = by_type.get(event_type, 0) + calls
        else:
            skipped += 1
    
    return {
        'total_calls': total_calls,
        'by_type': by_type,
        'events_processed': len(events),
        'events_skipped': skipped,
        'estimated_cost': round(total_calls * 0.007, 2)
    }


if __name__ == "__main__":
    """
    Test collection rules
    """
    print("=" * 70)
    print("Traffic Collection Rules Test")
    print("=" * 70)
    print()
    
    # Test events
    test_events = [
        {
            'event_name': 'Isotopes Baseball',
            'category': 'Sports',
            'is_multi_day': False,
            'event_start_time': '18:35:00'
        },
        {
            'event_name': 'Art Gallery Opening',
            'category': 'Arts & Culture',
            'is_multi_day': False,
            'event_start_time': '19:00:00'
        },
        {
            'event_name': 'Balloon Fiesta',
            'category': 'Festival',
            'is_multi_day': True,
            'event_start_time': '06:00:00'
        },
        {
            'event_name': 'Conference',
            'category': 'General',
            'is_multi_day': True,
            'event_start_time': None
        }
    ]
    
    for event in test_events:
        print(f"Event: {event['event_name']}")
        print(f"  Category: {event['category']}")
        print(f"  Multi-day: {event['is_multi_day']}")
        
        plan = get_collection_plan(event)
        
        if plan['collect']:
            print(f"  ✓ Collect: {plan['type']}")
            print(f"    Before: {plan['collect_before']}, After: {plan['collect_after']}")
            print(f"    Directions: {plan['num_directions']} ({', '.join(plan['directions'])})")
            print(f"    API calls: {plan['estimated_calls']}")
        else:
            print(f"  ✗ Skip: {plan['reason']}")
        
        print()
    
    # Estimate for test set
    estimate = estimate_monthly_api_calls(test_events)
    print("Estimate for test events:")
    print(f"  Total calls: {estimate['total_calls']}")
    print(f"  By type: {estimate['by_type']}")
    print(f"  Cost: ${estimate['estimated_cost']}")