"""
Generate static HTML dashboard with interactive charts.
Creates a self-contained HTML file that can be shared.
"""

import sys
sys.path.append('C:\\Users\\lanee\\Desktop\\whatspoppingABQ')

from database.db_utils import query_to_dataframe
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

print("=" * 70)
print("Generating HTML Dashboard")
print("=" * 70)
print()

print("=" * 70)
print("Generating HTML Dashboard")
print("=" * 70)
print()

# Load data using new function
events_query = """
    SELECT 
        e.event_id,
        e.event_name,
        e.event_start_date,
        e.category,
        v.venue_name,
        v.latitude,
        v.longitude,
        eis.avg_delay_before,
        eis.avg_delay_during,
        (eis.avg_delay_after - eis.avg_delay_before) as impact_minutes
    FROM events e
    JOIN venue_locations v ON e.venue_id = v.venue_id
    JOIN event_impact_summary eis ON e.event_id = eis.event_id
    WHERE eis.avg_delay_before IS NOT NULL
      AND eis.avg_delay_after IS NOT NULL
"""

events_df = query_to_dataframe(events_query)

# Convert Decimal to float
numeric_cols = ['latitude', 'longitude', 'avg_delay_before', 
                'avg_delay_during', 'impact_minutes']

for col in numeric_cols:
    if col in events_df.columns:
        events_df[col] = pd.to_numeric(events_df[col], errors='coerce')

category_query = "SELECT * FROM category_traffic_impact ORDER BY avg_impact_minutes DESC"
category_df = query_to_dataframe(category_query)

# Convert numeric columns
numeric_cols = ['event_count', 'avg_impact_minutes', 'max_impact_minutes']

for col in numeric_cols:
    if col in category_df.columns:
        category_df[col] = pd.to_numeric(category_df[col], errors='coerce')

print(f"Loaded {len(events_df)} events")
print(f"Loaded {len(category_df)} categories")
print()

# Add impact level
events_df['impact_level'] = pd.cut(
    events_df['impact_minutes'],
    bins=[-float('inf'), 1, 2, 5, float('inf')],
    labels=['Low', 'Moderate', 'High', 'Severe']
)

# Create dashboard
print("Creating visualizations...")

# 1. Category bar chart
fig_category = px.bar(
    category_df,
    x='category',
    y='avg_impact_minutes',
    title='Average Traffic Impact by Event Category',
    labels={'avg_impact_minutes': 'Average Delay (minutes)', 'category': 'Category'},
    color='avg_impact_minutes',
    color_continuous_scale='RdYlGn_r'
)
fig_category.update_layout(xaxis_tickangle=-45, height=500)

# 2. Impact pie chart
impact_counts = events_df['impact_level'].value_counts()
fig_pie = px.pie(
    values=impact_counts.values,
    names=impact_counts.index,
    title='Event Distribution by Impact Level',
    color=impact_counts.index,
    color_discrete_map={
        'Low': '#90EE90',
        'Moderate': '#FFD700',
        'High': '#FFA500',
        'Severe': '#FF4500'
    }
)

# 3. Timeline scatter
fig_timeline = px.scatter(
    events_df,
    x='event_start_date',
    y='impact_minutes',
    color='category',
    hover_data=['event_name', 'venue_name'],
    title='Traffic Impact Over Time',
    labels={'impact_minutes': 'Traffic Delay (minutes)', 'event_start_date': 'Date'}
)
fig_timeline.add_hline(y=2, line_dash="dash", line_color="orange")
fig_timeline.add_hline(y=5, line_dash="dash", line_color="red")
fig_timeline.update_layout(height=500)

# 4. Map
fig_map = px.scatter_mapbox(
    events_df,
    lat='latitude',
    lon='longitude',
    color='impact_minutes',
    size='impact_minutes',
    hover_name='event_name',
    hover_data=['venue_name', 'category'],
    color_continuous_scale='RdYlGn_r',
    zoom=10,
    height=600,
    title='Event Locations by Traffic Impact'
)
fig_map.update_layout(
    mapbox_style="open-street-map",
    mapbox_center={"lat": 35.0844, "lon": -106.6504}
)

# Create HTML
print("Generating HTML file...")

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>ABQ Event Traffic Impact Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        .metrics {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
        }}
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            color: #7f8c8d;
            margin-top: 10px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .footer {{
            text-align: center;
            color: #999;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <h1>🚗 Albuquerque Event Traffic Impact Dashboard</h1>
    <p class="subtitle">Analyzing how events affect local traffic patterns</p>
    
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{len(events_df)}</div>
            <div class="metric-label">Events Analyzed</div>
        </div>
        <div class="metric">
            <div class="metric-value">{events_df['impact_minutes'].mean():.1f} min</div>
            <div class="metric-label">Average Impact</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(events_df[events_df['impact_level'].isin(['High', 'Severe'])])}</div>
            <div class="metric-label">High Impact Events</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(category_df)}</div>
            <div class="metric-label">Event Categories</div>
        </div>
    </div>
    
    <div class="chart-container">
        <div id="category-chart"></div>
    </div>
    
    <div class="chart-container">
        <div id="pie-chart"></div>
    </div>
    
    <div class="chart-container">
        <div id="timeline-chart"></div>
    </div>
    
    <div class="chart-container">
        <div id="map-chart"></div>
    </div>
    
    <div class="footer">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        What's Popping ABQ - Event Traffic Analytics
    </div>
    
    <script>
        {fig_category.to_html(include_plotlyjs=False, div_id="category-chart")}
        {fig_pie.to_html(include_plotlyjs=False, div_id="pie-chart")}
        {fig_timeline.to_html(include_plotlyjs=False, div_id="timeline-chart")}
        {fig_map.to_html(include_plotlyjs=False, div_id="map-chart")}
    </script>
</body>
</html>
"""

# Save HTML
filename = f"traffic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

with open(filename, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✓ Dashboard saved to: {filename}")
print()
print("You can:")
print("  1. Open it in your browser")
print("  2. Share the HTML file")
print("  3. Host it on GitHub Pages")
print()
print("=" * 70)