"""
Generate comprehensive traffic impact report.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from analysis.event_traffic_correlation import (
    analyze_all_events,
    get_impact_summary
)
from datetime import datetime

print("=" * 70)
print("EVENT TRAFFIC IMPACT REPORT")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

# Analyze
analyses = analyze_all_events()

if not analyses:
    print("⚠️  No events with traffic data found")
    print()
    print("To generate report:")
    print("  1. Ensure events have times in database")
    print("  2. Run traffic collection (hourly)")
    print("  3. Wait for events to occur and traffic to be collected")
    exit(0)

summary = get_impact_summary(analyses)

# Report sections
print("EXECUTIVE SUMMARY")
print("-" * 70)
print(f"Events analyzed: {summary['total_events_analyzed']}")
print()

if summary['impact_levels']:
    print("Traffic Impact Distribution:")
    for level in ['severe', 'high', 'moderate', 'low', 'unknown']:
        count = summary['impact_levels'].get(level, 0)
        if count > 0:
            pct = count * 100 / summary['total_events_analyzed']
            print(f"  {level.capitalize():10s}: {count:3d} events ({pct:5.1f}%)")
print()

print("CATEGORY ANALYSIS")
print("-" * 70)
print("Average traffic delay increase by event category:")
print()

for cat, avg_delay in sorted(
    summary['category_avg_impact'].items(),
    key=lambda x: x[1],
    reverse=True
):
    print(f"  {cat:35s}: +{avg_delay:6.2f} minutes")
    
    # Determine recommendation
    if avg_delay > 5:
        rec = "⚠️  HIGH IMPACT - Consider traffic management"
    elif avg_delay > 2:
        rec = "⚠️  MODERATE IMPACT - Monitor traffic"
    elif avg_delay > 1:
        rec = "✓ LOW IMPACT"
    else:
        rec = "✓ MINIMAL IMPACT"
    
    print(f"     {rec}")
    print()

print()
print("TOP IMPACT EVENTS")
print("-" * 70)
print("Events causing the most traffic disruption:")
print()

for i, event in enumerate(summary['top_impact_events'][:10], 1):
    print(f"{i}. {event['event_name']}")
    print(f"   Venue: {event['venue']}")
    print(f"   Category: {event['category']}")
    print(f"   Traffic Impact: +{event['delay_increase']:.1f} min ({event['impact_level'].upper()})")
    print()

print()
print("RECOMMENDATIONS")
print("-" * 70)

# Generate recommendations based on data
high_impact_cats = [
    cat for cat, delay in summary['category_avg_impact'].items()
    if delay > 2
]

if high_impact_cats:
    print("High-impact event categories:")
    for cat in high_impact_cats:
        print(f"  • {cat} (avg +{summary['category_avg_impact'][cat]:.1f} min)")
    print()
else:
    print("✓ No categories show consistently high traffic impact")

print()
print("=" * 70)
print("END OF REPORT")
print("=" * 70)

# Save report to file
filename = f"traffic_impact_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

with open(filename, 'w') as f:
    f.write("EVENT TRAFFIC IMPACT REPORT\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n\n")
    
    # Write summary sections (simplified for file)
    f.write(f"Total events analyzed: {summary['total_events_analyzed']}\n\n")
    
    f.write("Impact Levels:\n")
    for level, count in summary['impact_levels'].items():
        f.write(f"  {level}: {count}\n")
    
    f.write("\nCategory Average Impact:\n")
    for cat, delay in summary['category_avg_impact'].items():
        f.write(f"  {cat}: +{delay:.2f} min\n")
    
    f.write("\nTop Impact Events:\n")
    for i, event in enumerate(summary['top_impact_events'][:10], 1):
        f.write(f"{i}. {event['event_name']} - {event['category']}\n")
        f.write(f"   Impact: +{event['delay_increase']:.1f} min\n")

print(f"\n✓ Report saved to: {filename}")