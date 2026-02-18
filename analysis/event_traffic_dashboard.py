"""
Interactive Event Traffic Impact Dashboard
Run with: streamlit run dashboard/event_traffic_dashboard.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db_utils import get_connection, query_to_dataframe
from datetime import datetime

# Page config
st.set_page_config(
    page_title="ABQ Event Traffic Dashboard",
    page_icon="",
    layout="wide"
)

# Title
st.title("Albuquerque Event Traffic Impact Dashboard")
st.markdown("*Analyzing how events affect local traffic patterns*")
st.markdown("---")

# Load data
@st.cache_data(ttl=3600)
def load_event_data():
    """Load event impact data from database"""
    
    query = """
        SELECT 
            event_id,
            event_name,
            event_start_date,
            event_start_time,
            category,
            venue_name,
            latitude,
            longitude,
            event_measurements,
            baseline_measurements,
            event_avg_delay,
            baseline_avg_delay,
            baseline_avg_speed,
            event_avg_speed,
            impact_above_baseline,
            impact_level,
            data_quality
        FROM event_impact_detail
       -- WHERE data_quality IN ('complete', 'partial')
       --   AND event_measurements > 0
        ORDER BY event_start_date DESC
    """
    
    df = query_to_dataframe(query)
    
    # Convert Decimal to float
    numeric_cols = ['latitude', 'longitude', 'event_avg_delay', 
                    'baseline_avg_delay', 'impact_above_baseline']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    # Derive commonly-used dashboard columns for compatibility
    # 'impact_minutes' expected by visualizations -> use 'impact_above_baseline' if present
    if 'impact_above_baseline' in df.columns:
        df['impact_minutes'] = pd.to_numeric(df['impact_above_baseline'], errors='coerce')
    elif 'event_avg_delay' in df.columns and 'baseline_avg_delay' in df.columns:
        df['impact_minutes'] = pd.to_numeric(df['event_avg_delay'], errors='coerce') - pd.to_numeric(df['baseline_avg_delay'], errors='coerce')

    # 'measurement_count' used for bubble sizes -> map from 'event_measurements' if available
    if 'event_measurements' in df.columns:
        df['measurement_count'] = pd.to_numeric(df['event_measurements'], errors='coerce')
    # Ensure measurement_count is numeric and non-null for plotting sizes
    if 'measurement_count' in df.columns:
        df['measurement_count'] = pd.to_numeric(df['measurement_count'], errors='coerce').fillna(0).clip(lower=0)

    return df

@st.cache_data(ttl=3600)
def load_category_data():
    """Load category impact data"""
    
    query = """
        SELECT 
            category,
            event_count,
            events_with_baseline,
            avg_impact_minutes,
            max_impact_minutes,
            avg_event_speed,
            avg_baseline_speed,
            avg_speed_difference,
            pct_high_impact
        FROM category_traffic_impact
        ORDER BY avg_impact_minutes DESC NULLS LAST
    """
    
    df = query_to_dataframe(query)
    
    # Convert numeric columns
    numeric_cols = ['event_count', 'events_with_baseline', 'avg_impact_minutes', 
                    'max_impact_minutes', 'avg_event_speed', 'avg_baseline_speed',
                    'avg_speed_difference', 'pct_high_impact']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


@st.cache_data(ttl=3600)
def load_baseline_patterns():
    """Load baseline traffic patterns"""
    
    query = """
        SELECT 
            venue_name,
            day_name,
            hour_of_day,
            avg_delay,
            avg_speed,
            typical_traffic_level,
            measurement_count
        FROM venue_baseline_patterns
        ORDER BY venue_name, day_of_week, hour_of_day
    """
    
    df = query_to_dataframe(query)
    
    # Convert numeric columns
    numeric_cols = ['hour_of_day', 'avg_delay', 'avg_speed', 'measurement_count']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

# Load data
# After loading data
try:
    events_df = load_event_data()
    category_df = load_category_data()
    baseline_df = load_baseline_patterns()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Category filter
    categories = ['All'] + sorted(events_df['category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Event Category", categories)
    
    # Impact level filter
    impact_levels = ['All'] + ['severe', 'high', 'moderate', 'low', 'none', 'unknown']
    selected_impact = st.sidebar.selectbox("Impact Level", impact_levels)
    
    # Data quality filter
    quality_options = ['All', 'complete', 'partial']
    selected_quality = st.sidebar.selectbox("Data Quality", quality_options)
    
    # Filter data
    filtered_df = events_df.copy()

# Debug: inspect filtered_df (toggleable)
    if st.sidebar.checkbox("Show debug: filtered_df"):
        st.markdown("**filtered_df diagnostics**")
        st.write("shape:", filtered_df.shape)
        st.write("columns:", filtered_df.columns.tolist())
        st.write("dtypes:")
        st.write(filtered_df.dtypes)
        st.write("non-null counts:")
        st.write(filtered_df.count())
        st.write("null counts:")
        st.write(filtered_df.isna().sum())
        if filtered_df.empty:
            st.error("filtered_df is EMPTY — no rows match current filters")
        else:
            st.dataframe(filtered_df.head(50), use_container_width=True)

    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if selected_impact != 'All':
        filtered_df = filtered_df[filtered_df['impact_level'] == selected_impact]
    if selected_quality != 'All':
        filtered_df = filtered_df[filtered_df['data_quality'] == selected_quality]
    
    # Ensure event_start_date is in datetime format
    if 'event_start_date' in filtered_df.columns:
        filtered_df['event_start_date'] = pd.to_datetime(filtered_df['event_start_date'], errors='coerce')

    # Filter data to only include events from the current month
    current_month = datetime.now().month
    current_year = datetime.now().year
    filtered_df = filtered_df[(filtered_df['event_start_date'].dt.month == current_month) &
                              (filtered_df['event_start_date'].dt.year == current_year)]
    
    # Ensure impact_above_baseline is numeric, non-negative, and has no NaN values
    if 'impact_above_baseline' in filtered_df.columns:
        filtered_df['impact_above_baseline'] = pd.to_numeric(filtered_df['impact_above_baseline'], errors='coerce').fillna(0).clip(lower=0)

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events Analyzed", len(events_df[events_df['event_measurements'] > 0]))
    
    with col2:
        avg_impact = events_df['impact_above_baseline'].mean()
        st.metric("Avg Impact Above Baseline", f"{avg_impact:.1f} min" if pd.notna(avg_impact) else "N/A")
    
    with col3:
        complete_data = len(events_df[(events_df['baseline_measurements'] > 0) & (events_df['event_measurements'] > 0)])
        st.metric("Events with Baseline", complete_data)
    
    with col4:
        high_impact = len(events_df[events_df['impact_level'].isin(['high', 'severe'])])
        st.metric("High Impact Events", high_impact)
    
    st.markdown("---")
    
    # Two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(" Impact Above Baseline by Category")
        
        # Filter out categories with no baseline data
        cat_with_baseline = category_df[category_df['avg_impact_minutes'].notna()]
        
        fig_category = px.bar(
            cat_with_baseline,
            x='category',
            y='avg_impact_minutes',
            title='Average Traffic Impact vs Baseline',
            labels={'avg_impact_minutes': 'Minutes Above Baseline', 'category': 'Category'},
            color='avg_impact_minutes',
            color_continuous_scale='RdYlGn_r',
            hover_data=['events_with_baseline', 'pct_high_impact']
        )
        fig_category.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig_category, use_container_width=True)
    
    with col2:
        st.subheader(" Data Quality Distribution")
        
        quality_counts = events_df[events_df['data_quality'] != 'no_event_data']['data_quality'].value_counts()
        
        fig_quality = px.pie(
            values=quality_counts.values,
            names=quality_counts.index,
            title='Event Data Quality',
            color=quality_counts.index,
            color_discrete_map={
                'excellent': "#57F057",
                'good': "#F8D640",
                'fair': "#FF5100",
                'no_event_data': '#FF4500'
            }
        )
        fig_quality.update_layout(height=400)
        st.plotly_chart(fig_quality, use_container_width=True)
    
    # Event vs Baseline comparison
    st.subheader(" Event Traffic vs Baseline")
    
    # Only show events with both measurements
    comparison_df = filtered_df[
        (filtered_df['event_avg_speed'].notna()) & 
        (filtered_df['baseline_avg_speed'].notna())
    ].copy()
    
    if len(comparison_df) > 0:
        # Create comparison chart
        comparison_df['Event Traffic'] = comparison_df['event_avg_speed']
        comparison_df['Baseline Traffic'] = comparison_df['baseline_avg_speed']
        
        fig_comparison = go.Figure()
        
        fig_comparison.add_trace(go.Scatter(
            x=comparison_df['event_name'],
            y=comparison_df['Baseline Traffic'],
            name='Baseline (Same Day/Hour)',
            mode='markers',
            marker=dict(size=10, color='green', symbol='circle')
        ))
        
        fig_comparison.add_trace(go.Scatter(
            x=comparison_df['event_name'],
            y=comparison_df['Event Traffic'],
            name='Event Traffic',
            mode='markers',
            marker=dict(size=10, color='red', symbol='diamond')
        ))
        
        fig_comparison.update_layout(
            title='Event Speed vs Baseline Speed',
            xaxis_title='Event',
            yaxis_title='Speed (mph)',
            height=600,
            hovermode='closest'
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
    else:
        st.info("No events with both event and baseline data available for comparison")
    
    # Timeline chart
    st.subheader("Traffic Impact Over Time")
    
    timeline_df = filtered_df.sort_values('event_start_date')

    fig_timeline = px.scatter(
        timeline_df,
        x='event_start_date',
        y='impact_minutes',
        color='category',
        size='impact_above_baseline',  # Use cleaned impact_above_baseline for sizing
        hover_data=['event_name', 'venue_name'],
        title='Event Traffic Impact Timeline',
        labels={'impact_minutes': 'Traffic Delay (minutes)', 'event_start_date': 'Event Date'}
    )
    fig_timeline.add_hline(y=2, line_dash="dash", line_color="orange", 
                           annotation_text="Moderate Impact Threshold")
    fig_timeline.add_hline(y=5, line_dash="dash", line_color="red",
                           annotation_text="High Impact Threshold")
    fig_timeline.update_layout(height=400)
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Map
    st.subheader("Event Locations & Traffic Impact")
    
    # Create map with Plotly
    map_df = filtered_df.copy()
    # Use cleaned impact_above_baseline for marker sizing
    map_df['map_size'] = map_df['impact_above_baseline']

    fig_map = px.scatter_mapbox(
        map_df,
        lat='latitude',
        lon='longitude',
        color='impact_minutes',
        size='map_size',
        hover_name='event_name',
        hover_data=['venue_name', 'category', 'impact_minutes'],
        color_continuous_scale='RdYlGn_r',
        zoom=10,
        height=500,
        title='Events by Location and Impact'
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        mapbox_center={"lat": 35.0844, "lon": -106.6504}  # Albuquerque center
    )

    st.plotly_chart(fig_map, use_container_width=True)
    
    # Top events table
    st.subheader("Top Impact Events")
    
    top_events = filtered_df.nlargest(10, 'impact_above_baseline')[
        ['event_name', 'venue_name', 'category', 'event_start_date', 'impact_above_baseline', 'impact_level']
    ]
    
    # Style the dataframe
    st.dataframe(
        top_events,
        column_config={
            "event_name": "Event",
            "venue_name": "Venue",
            "category": "Category",
            "event_start_date": st.column_config.DateColumn("Date"),
            "impact_above_baseline": st.column_config.NumberColumn("Impact Above Baseline", format="%.1f"),
            "impact_level": "Level"
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Detailed data (expandable)
    with st.expander("View All Event Data"):
        st.dataframe(filtered_df, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data: {len(events_df)} events analyzed")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Make sure you have event and traffic data in the database. Run sample data generation if needed.")