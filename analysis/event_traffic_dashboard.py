
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
    page_icon="🚗",
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
            e.event_id,
            e.event_name,
            e.event_start_date,
            e.category,
            v.venue_name,
            v.latitude,
            v.longitude,
            eis.measurement_count,
            eis.avg_delay_before,
            eis.avg_delay_during,
            eis.avg_delay_after,
            (eis.avg_delay_after - eis.avg_delay_before) as impact_minutes
        FROM events e
        JOIN venue_locations v ON e.venue_id = v.venue_id
        JOIN event_impact_summary eis ON e.event_id = eis.event_id
        WHERE eis.avg_delay_before IS NOT NULL
          AND eis.avg_delay_after IS NOT NULL
    """
    
    df = query_to_dataframe(query)
    
    # Convert Decimal columns to float
    numeric_cols = ['latitude', 'longitude', 'measurement_count', 
                    'avg_delay_before', 'avg_delay_during', 'avg_delay_after', 
                    'impact_minutes']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Add impact level
    df['impact_level'] = pd.cut(
        df['impact_minutes'],
        bins=[-float('inf'), 1, 2, 5, float('inf')],
        labels=['Low', 'Moderate', 'High', 'Severe']
    )
    
    return df

@st.cache_data(ttl=3600)
def load_category_data():
    """Load category impact data"""
    
    query = """
        SELECT * FROM category_traffic_impact
        ORDER BY avg_impact_minutes DESC
    """
    
    df = query_to_dataframe(query)
    
    # Convert numeric columns
    numeric_cols = ['event_count', 'avg_impact_minutes', 'max_impact_minutes']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

# Load data
try:
    events_df = load_event_data()
    category_df = load_category_data()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Category filter
    categories = ['All'] + sorted(events_df['category'].unique().tolist())
    selected_category = st.sidebar.selectbox("Event Category", categories)
    
    # Impact level filter
    impact_levels = ['All'] + events_df['impact_level'].cat.categories.tolist()
    selected_impact = st.sidebar.selectbox("Impact Level", impact_levels)
    
    # Filter data
    filtered_df = events_df.copy()
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    if selected_impact != 'All':
        filtered_df = filtered_df[filtered_df['impact_level'] == selected_impact]
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events Analyzed", len(events_df))
    
    with col2:
        avg_impact = events_df['impact_minutes'].mean()
        st.metric("Average Traffic Impact", f"{avg_impact:.1f} min")
    
    with col3:
        high_impact = len(events_df[events_df['impact_level'].isin(['High', 'Severe'])])
        st.metric("High Impact Events", high_impact)
    
    with col4:
        total_measurements = events_df['measurement_count'].sum()
        st.metric("Traffic Measurements", int(total_measurements))
    
    st.markdown("---")
    
    # Two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Traffic Impact by Category")
        
        fig_category = px.bar(
            category_df,
            x='category',
            y='avg_impact_minutes',
            title='Average Traffic Delay by Event Category',
            labels={'avg_impact_minutes': 'Avg Delay (minutes)', 'category': 'Category'},
            color='avg_impact_minutes',
            color_continuous_scale='RdYlGn_r'
        )
        fig_category.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig_category, use_container_width=True)
    
    with col2:
        st.subheader("Impact Level Distribution")
        
        impact_counts = filtered_df['impact_level'].value_counts()
        
        fig_impact = px.pie(
            values=impact_counts.values,
            names=impact_counts.index,
            title='Events by Impact Level',
            color=impact_counts.index,
            color_discrete_map={
                'Low': '#90EE90',
                'Moderate': '#FFD700',
                'High': '#FFA500',
                'Severe': '#FF4500'
            }
        )
        fig_impact.update_layout(height=400)
        st.plotly_chart(fig_impact, use_container_width=True)
    
    # Timeline chart
    st.subheader("Traffic Impact Over Time")
    
    timeline_df = filtered_df.sort_values('event_start_date')
    
    fig_timeline = px.scatter(
        timeline_df,
        x='event_start_date',
        y='impact_minutes',
        color='category',
        size='measurement_count',
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
    fig_map = px.scatter_mapbox(
        filtered_df,
        lat='latitude',
        lon='longitude',
        color='impact_minutes',
        size='impact_minutes',
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
    
    top_events = filtered_df.nlargest(10, 'impact_minutes')[
        ['event_name', 'venue_name', 'category', 'event_start_date', 'impact_minutes', 'impact_level']
    ]
    
    # Style the dataframe
    st.dataframe(
        top_events,
        column_config={
            "event_name": "Event",
            "venue_name": "Venue",
            "category": "Category",
            "event_start_date": st.column_config.DateColumn("Date"),
            "impact_minutes": st.column_config.NumberColumn("Impact (min)", format="%.1f"),
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