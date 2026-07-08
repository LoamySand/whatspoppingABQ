"""
Interactive Event Traffic Impact Dashboard
Run with: streamlit run analysis/event_traffic_dashboard.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

# Page config
st.set_page_config(page_title="ABQ Event Traffic Dashboard", page_icon="", layout="wide")

st.title(" Albuquerque Event Traffic Impact Dashboard")
st.markdown("*Analyzing how events affect local traffic patterns*")
st.markdown("---")

# Fail fast on missing DB config -- but only when running against a local
# .env (e.g. self-hosted). On Streamlit Cloud, credentials live in st.secrets instead, so skip this check.
if not (hasattr(st, "secrets") and "DB_HOST" in st.secrets):
    from utils.config_validation import validate_env

    validate_env("database", service_name="Dashboard (analysis/event_traffic_dashboard.py)")


# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────


def get_db_connection():
    import os as os_module

    from dotenv import load_dotenv

    project_root = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))
    env_path = os_module.path.join(project_root, ".env")
    load_dotenv(dotenv_path=env_path, override=True)

    try:
        if hasattr(st, "secrets") and "DB_HOST" in st.secrets:
            return psycopg2.connect(
                host=st.secrets["DB_HOST"],
                port=int(st.secrets.get("DB_PORT", 6543)),
                database=st.secrets["DB_NAME"],
                user=st.secrets["DB_USER"],
                password=st.secrets["DB_PASSWORD"],
                sslmode="require",
                connect_timeout=10,
            )
    except (AttributeError, FileNotFoundError, KeyError):
        pass

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require" if "supabase" in os.getenv("DB_HOST", "") else "prefer",
        connect_timeout=10,
    )


def query_to_dataframe(query):
    conn = None
    try:
        conn = get_db_connection()
        df = pd.read_sql(query, conn)
        return df
    finally:
        if conn and not conn.closed:
            conn.close()


# ─────────────────────────────────────────────
# Data loaders
# ─────────────────────────────────────────────


@st.cache_data(ttl=3600)
def load_event_data():
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
            baseline_match_type,
            baseline_confidence,
            event_avg_delay,
            baseline_avg_delay,
            event_avg_speed,
            baseline_avg_speed,
            speed_difference_mph,
            speed_reduction_pct,
            impact_from_delay,
            impact_from_speed,
            impact_level,
            data_quality
        FROM app.event_impact_detail
        ORDER BY event_start_date DESC
    """
    df = query_to_dataframe(query)

    numeric_cols = [
        "latitude",
        "longitude",
        "event_avg_delay",
        "baseline_avg_delay",
        "impact_from_speed",
        "event_avg_speed",
        "baseline_avg_speed",
        "speed_difference_mph",
        "impact_from_delay",
        "speed_reduction_pct",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "event_measurements" in df.columns:
        df["measurement_count"] = pd.to_numeric(df["event_measurements"], errors="coerce").fillna(0)

    return df


@st.cache_data(ttl=3600)
def load_category_data():
    query = """
        SELECT
            category,
            event_count,
            events_with_baseline,
            avg_impact_minutes,
            avg_speed_reduction_pct,
            max_impact_minutes,
            avg_event_speed,
            avg_baseline_speed,
            avg_speed_difference,
            pct_high_impact
        FROM app.category_traffic_impact
        ORDER BY avg_speed_reduction_pct DESC NULLS LAST
    """
    df = query_to_dataframe(query)

    numeric_cols = [
        "event_count",
        "events_with_baseline",
        "avg_impact_minutes",
        "avg_speed_reduction_pct",
        "max_impact_minutes",
        "avg_event_speed",
        "avg_baseline_speed",
        "avg_speed_difference",
        "pct_high_impact",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


@st.cache_data(ttl=3600)
def load_baseline_patterns():
    query = """
        SELECT
            venue_name,
            day_name,
            hour_of_day,
            avg_delay,
            avg_speed,
            typical_traffic_level,
            measurement_count
        FROM app.venue_baseline_patterns
        ORDER BY venue_name, day_of_week, hour_of_day
    """
    df = query_to_dataframe(query)

    numeric_cols = ["hour_of_day", "avg_delay", "avg_speed", "measurement_count"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

QUALITY_COLORS = {
    "excellent": "#22c55e",
    "good": "#84cc16",
    "fair": "#f59e0b",
    "poor": "#ef4444",
    "unreliable": "#a855f7",
    "no_event_data": "#6b7280",
    "no_baseline_data": "#3b82f6",
    "unknown": "#d1d5db",
}

CONFIDENCE_COLORS = {
    "high": "#22c55e",
    "medium": "#84cc16",
    "low": "#f59e0b",
    "insufficient": "#ef4444",
    "none": "#6b7280",
}

CONFIDENCE_ORDER = ["high", "medium", "low", "insufficient", "none"]
QUALITY_ORDER = [
    "excellent",
    "good",
    "fair",
    "poor",
    "unreliable",
    "no_baseline_data",
    "no_event_data",
    "unknown",
]

# Speed reduction thresholds (%) for impact tiers
THRESHOLDS = {"severe": 30, "high": 15, "moderate": 8}


# ─────────────────────────────────────────────
# Main app
# ─────────────────────────────────────────────

try:
    events_df = load_event_data()
    category_df = load_category_data()
    baseline_df = load_baseline_patterns()

    # ── Sidebar filters ──────────────────────
    st.sidebar.header("Filters")

    categories = ["All"] + sorted(events_df["category"].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("Event Category", categories)

    impact_levels = ["All"] + ["severe", "high", "moderate", "low", "none", "unknown"]
    selected_impact = st.sidebar.selectbox("Impact Level", impact_levels)

    st.sidebar.markdown("**Data Quality**")
    available_qualities = sorted(
        events_df["data_quality"].dropna().unique().tolist(),
        key=lambda x: QUALITY_ORDER.index(x) if x in QUALITY_ORDER else 99,
    )
    selected_qualities = st.sidebar.multiselect(
        "Show data quality:",
        options=available_qualities,
        default=[
            q for q in available_qualities if q not in ("no_event_data", "unreliable", "unknown")
        ],
        help="'Unreliable' = baseline had only one measurement.",
    )

    st.sidebar.markdown("**Baseline Confidence**")
    available_confidence = [
        c
        for c in CONFIDENCE_ORDER
        if c in events_df["baseline_confidence"].dropna().unique().tolist()
    ]
    selected_confidence = st.sidebar.multiselect(
        "Show confidence levels:",
        options=available_confidence,
        default=[c for c in available_confidence if c != "insufficient"],
        help="High = 10+, Medium = 5–9, Low = 2–4, Insufficient = 1 measurement.",
    )

    st.sidebar.markdown("**Date Range**")
    events_df["event_start_date"] = pd.to_datetime(events_df["event_start_date"], errors="coerce")
    min_date = events_df["event_start_date"].min()
    max_date = events_df["event_start_date"].max()
    picker_min = min_date.date() if pd.notna(min_date) else datetime(2020, 1, 1).date()
    picker_max = max_date.date() if pd.notna(max_date) else datetime.now().date()

    # Clamped, not just "1st of this month" -- if the data is stale (e.g.
    # the scraper hasn't run recently) and the latest event is earlier than
    # the 1st of the current month, an unclamped default_start > picker_max
    # produces a reversed (start, end) tuple. Streamlit's date_input passes
    # that straight to the frontend calendar component, which throws
    # "RangeError: Invalid interval" trying to render an impossible range.
    default_start = min(datetime.now().replace(day=1).date(), picker_max)
    default_start = max(default_start, picker_min)

    date_range = st.sidebar.date_input(
        "Select range",
        value=(default_start, picker_max),
        min_value=picker_min,
        max_value=picker_max,
    )

    # ── Apply filters ────────────────────────
    filtered_df = events_df.copy()

    if selected_category != "All":
        filtered_df = filtered_df[filtered_df["category"] == selected_category]
    if selected_impact != "All":
        filtered_df = filtered_df[filtered_df["impact_level"] == selected_impact]
    if selected_qualities:
        filtered_df = filtered_df[filtered_df["data_quality"].isin(selected_qualities)]
    if selected_confidence:
        filtered_df = filtered_df[
            filtered_df["baseline_confidence"].isin(selected_confidence)
            | filtered_df["baseline_confidence"].isna()
        ]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df["event_start_date"] >= pd.Timestamp(start_date))
            & (filtered_df["event_start_date"] <= pd.Timestamp(end_date))
        ]

    # ── Reliable subset for top-line metrics ─
    reliable_events = filtered_df[
        (filtered_df["event_measurements"] > 0)
        & (~filtered_df["baseline_confidence"].isin(["insufficient", "none"]))
    ]

    # ── Key metrics ──────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Events Analyzed", len(filtered_df[filtered_df["event_measurements"] > 0]))

    with col2:
        avg_reduction = reliable_events["speed_reduction_pct"].mean()
        st.metric(
            "Avg Speed Reduction",
            f"{avg_reduction:.1f}%" if pd.notna(avg_reduction) else "N/A",
            help="Average speed reduction % across reliable events",
        )

    with col3:
        st.metric("Events with Reliable Baseline", len(reliable_events))

    with col4:
        high_impact = len(
            reliable_events[reliable_events["speed_reduction_pct"] > THRESHOLDS["high"]]
        )
        st.metric(
            "High Impact Events",
            high_impact,
            help=f"Events where roads were >{THRESHOLDS['high']}% slower than baseline",
        )

    st.markdown("---")

    # ── Charts row 1: Category bar + Quality pie ──
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(" Speed Reduction by Category")
        # Rebuild from filtered_df so sidebar filters apply
        cat_with_data = (
            filtered_df[
                filtered_df["speed_reduction_pct"].notna()
                & ~filtered_df["baseline_confidence"].isin(["insufficient", "none"])
            ]
            .groupby("category")
            .agg(
                avg_speed_reduction_pct=("speed_reduction_pct", "mean"),
                events_with_baseline=("event_id", "count"),
                avg_impact_minutes=("impact_from_speed", "mean"),
                pct_high_impact=(
                    "speed_reduction_pct",
                    lambda x: round((x > 15).sum() / len(x) * 100, 1),
                ),
            )
            .reset_index()
        )
        cat_with_data = cat_with_data[cat_with_data["avg_speed_reduction_pct"].notna()]

        if len(cat_with_data) > 0:
            fig_category = px.bar(
                cat_with_data,
                x="category",
                y="avg_speed_reduction_pct",
                title="Average Speed Reduction % by Category (reliable events only)",
                labels={
                    "avg_speed_reduction_pct": "Avg Speed Reduction (%)",
                    "category": "Category",
                },
                color="avg_speed_reduction_pct",
                color_continuous_scale="RdYlGn_r",
                hover_data=["events_with_baseline", "pct_high_impact", "avg_impact_minutes"],
            )
            fig_category.add_hline(
                y=THRESHOLDS["moderate"],
                line_dash="dash",
                line_color="gold",
                annotation_text="Moderate (8%)",
            )
            fig_category.add_hline(
                y=THRESHOLDS["high"],
                line_dash="dash",
                line_color="orange",
                annotation_text="High (15%)",
            )
            fig_category.add_hline(
                y=THRESHOLDS["severe"],
                line_dash="dash",
                line_color="red",
                annotation_text="Severe (30%)",
            )
            fig_category.update_layout(xaxis_tickangle=-45, height=420)
            st.plotly_chart(fig_category, use_container_width=True)
        else:
            st.info("No category data available")

    with col2:
        st.subheader(" Data Quality Distribution")
        quality_counts = filtered_df[filtered_df["data_quality"] != "no_event_data"][
            "data_quality"
        ].value_counts()

        if len(quality_counts) > 0:
            fig_quality = px.pie(
                values=quality_counts.values,
                names=quality_counts.index,
                title="Event Data Quality (all events)",
                color=quality_counts.index,
                color_discrete_map=QUALITY_COLORS,
            )
            fig_quality.update_layout(height=420)
            st.plotly_chart(fig_quality, use_container_width=True)
        else:
            st.info("No quality data available")

    # ── Baseline confidence breakdown ─────────
    st.subheader(" Baseline Confidence Breakdown")
    conf_col1, conf_col2 = st.columns(2)

    with conf_col1:
        conf_counts = (
            filtered_df["baseline_confidence"]
            .value_counts()
            .reindex(CONFIDENCE_ORDER, fill_value=0)
            .reset_index()
        )
        conf_counts.columns = ["confidence", "count"]

        fig_conf = px.bar(
            conf_counts,
            x="confidence",
            y="count",
            title="Events by Baseline Confidence Level",
            color="confidence",
            color_discrete_map=CONFIDENCE_COLORS,
            labels={"confidence": "Confidence", "count": "Event Count"},
        )
        fig_conf.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig_conf, use_container_width=True)

    with conf_col2:
        conf_reduction = (
            filtered_df[filtered_df["speed_reduction_pct"].notna()]
            .groupby("baseline_confidence")["speed_reduction_pct"]
            .mean()
            .reindex(CONFIDENCE_ORDER)
            .reset_index()
        )
        conf_reduction.columns = ["confidence", "avg_reduction"]

        fig_conf_reduction = px.bar(
            conf_reduction.dropna(),
            x="confidence",
            y="avg_reduction",
            title="Avg Speed Reduction % by Confidence Level",
            color="confidence",
            color_discrete_map=CONFIDENCE_COLORS,
            labels={"confidence": "Confidence", "avg_reduction": "Avg Speed Reduction (%)"},
        )
        fig_conf_reduction.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig_conf_reduction, use_container_width=True)

    # ── Event vs Baseline speed scatter ──────
    st.subheader(" Event Speed vs Baseline Speed")
    comparison_df = filtered_df[
        (filtered_df["event_avg_speed"].notna()) & (filtered_df["baseline_avg_speed"].notna())
    ].copy()

    if len(comparison_df) > 0:
        fig_comparison = go.Figure()

        fig_comparison.add_trace(
            go.Scatter(
                x=comparison_df["event_name"],
                y=comparison_df["baseline_avg_speed"],
                name="Baseline Speed",
                mode="markers",
                marker=dict(size=10, color="green", symbol="circle"),
                hovertemplate="%{x}<br>Baseline: %{y:.1f} mph<extra></extra>",
            )
        )

        fig_comparison.add_trace(
            go.Scatter(
                x=comparison_df["event_name"],
                y=comparison_df["event_avg_speed"],
                name="Event Speed",
                mode="markers",
                marker=dict(
                    size=10,
                    color=comparison_df["speed_reduction_pct"],
                    colorscale="RdYlGn_r",
                    symbol="diamond",
                    showscale=True,
                    colorbar=dict(title="Speed Reduction %"),
                ),
                hovertemplate=(
                    "%{x}<br>"
                    "Event speed: %{y:.1f} mph<br>"
                    "Speed reduction: "
                    + comparison_df["speed_reduction_pct"].round(1).astype(str)
                    + "%<br>"
                    + "Quality: "
                    + comparison_df["data_quality"].astype(str)
                    + "<extra></extra>"
                ),
            )
        )

        fig_comparison.update_layout(
            title="Event Speed vs Baseline — diamond color = speed reduction %",
            xaxis_title="Event",
            yaxis_title="Speed (mph)",
            height=600,
            hovermode="closest",
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
    else:
        st.info("No events with both event and baseline data for the selected filters")

    # ── Timeline ─────────────────────────────
    st.subheader(" Speed Reduction Over Time")
    timeline_df = (
        filtered_df[filtered_df["speed_reduction_pct"].notna()]
        .sort_values("event_start_date")
        .copy()
    )

    if len(timeline_df) > 0:
        timeline_df["bubble_size"] = (
            timeline_df["speed_reduction_pct"].abs().fillna(0.5).clip(lower=0.5)
        )
        fig_timeline = px.scatter(
            timeline_df,
            x="event_start_date",
            y="speed_reduction_pct",
            color="category",
            size="bubble_size",
            symbol="data_quality",
            hover_data={
                "event_name": True,
                "venue_name": True,
                "speed_reduction_pct": ":.1f",
                "impact_from_speed": ":.2f",
                "data_quality": True,
                "baseline_confidence": True,
                "bubble_size": False,
            },
            title="Speed Reduction % Over Time (positive = roads slower than normal)",
            labels={"speed_reduction_pct": "Speed Reduction (%)", "event_start_date": "Event Date"},
        )
        fig_timeline.add_hline(
            y=0, line_dash="solid", line_color="gray", opacity=0.5, annotation_text="No impact"
        )
        fig_timeline.add_hline(
            y=THRESHOLDS["moderate"],
            line_dash="dash",
            line_color="gold",
            annotation_text="Moderate (8%)",
        )
        fig_timeline.add_hline(
            y=THRESHOLDS["high"],
            line_dash="dash",
            line_color="orange",
            annotation_text="High (15%)",
        )
        fig_timeline.add_hline(
            y=THRESHOLDS["severe"],
            line_dash="dash",
            line_color="red",
            annotation_text="Severe (30%)",
        )
        fig_timeline.update_layout(height=450)
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("No timeline data available for the selected filters")

    # ── Map ───────────────────────────────────
    st.subheader(" Event Locations & Speed Reduction")
    map_df = filtered_df[
        filtered_df["latitude"].notna()
        & filtered_df["longitude"].notna()
        & filtered_df["speed_reduction_pct"].notna()
    ].copy()
    map_df["map_size"] = map_df["speed_reduction_pct"].abs().fillna(0.5).clip(lower=0.5)

    if len(map_df) > 0:
        fig_map = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            color="speed_reduction_pct",
            size="map_size",
            hover_name="event_name",
            hover_data={
                "venue_name": True,
                "category": True,
                "speed_reduction_pct": ":.1f",
                "impact_from_speed": ":.2f",
                "data_quality": True,
                "baseline_confidence": True,
                "latitude": False,
                "longitude": False,
                "map_size": False,
            },
            color_continuous_scale="RdYlGn_r",
            zoom=10,
            height=500,
            title="Events by Location — size and color = speed reduction %",
        )
        fig_map.update_layout(
            mapbox_style="open-street-map", mapbox_center={"lat": 35.0844, "lon": -106.6504}
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No map data for the selected filters — speed reduction % required for map display")

    # ── Top events table ──────────────────────
    st.subheader(" Top Impact Events")

    if len(filtered_df) > 0:
        rankable = filtered_df[filtered_df["speed_reduction_pct"].notna()]

        top_events = rankable.nlargest(10, "speed_reduction_pct")[
            [
                "event_name",
                "venue_name",
                "category",
                "event_start_date",
                "speed_reduction_pct",
                "impact_from_speed",
                "event_avg_speed",
                "baseline_avg_speed",
                "impact_level",
                "data_quality",
                "baseline_confidence",
            ]
        ].copy()

        top_events["event_start_date"] = pd.to_datetime(top_events["event_start_date"]).dt.strftime(
            "%Y-%m-%d"
        )
        top_events["speed_reduction_pct"] = top_events["speed_reduction_pct"].round(1)
        top_events["impact_from_speed"] = top_events["impact_from_speed"].round(2)
        top_events["event_avg_speed"] = top_events["event_avg_speed"].round(1)
        top_events["baseline_avg_speed"] = top_events["baseline_avg_speed"].round(1)

        top_events = top_events.rename(
            columns={
                "event_name": "Event",
                "venue_name": "Venue",
                "category": "Category",
                "event_start_date": "Date",
                "speed_reduction_pct": "Speed Reduction %",
                "impact_from_speed": "Impact (min)",
                "event_avg_speed": "Event Speed (mph)",
                "baseline_avg_speed": "Baseline Speed (mph)",
                "impact_level": "Level",
                "data_quality": "Quality",
                "baseline_confidence": "Confidence",
            }
        )

        try:
            st.dataframe(
                top_events,
                column_config={
                    "Event": st.column_config.TextColumn("Event"),
                    "Venue": st.column_config.TextColumn("Venue"),
                    "Category": st.column_config.TextColumn("Category"),
                    "Date": st.column_config.TextColumn("Date"),
                    "Speed Reduction %": st.column_config.NumberColumn(
                        "Speed Reduction %", format="%.1f%%"
                    ),
                    "Impact (min)": st.column_config.NumberColumn("Impact (min)", format="%.2f"),
                    "Event Speed (mph)": st.column_config.NumberColumn(
                        "Event Speed (mph)", format="%.1f"
                    ),
                    "Baseline Speed (mph)": st.column_config.NumberColumn(
                        "Baseline Speed (mph)", format="%.1f"
                    ),
                    "Level": st.column_config.TextColumn("Level"),
                    "Quality": st.column_config.TextColumn("Quality"),
                    "Confidence": st.column_config.TextColumn("Confidence"),
                },
                hide_index=True,
                use_container_width=True,
            )
        except AttributeError:
            st.dataframe(top_events, use_container_width=True)
    else:
        st.info("No events match the selected filters")

    # ── Raw data expander ─────────────────────
    with st.expander(" View All Event Data"):
        st.dataframe(filtered_df, use_container_width=True)

    # ── Footer ────────────────────────────────
    st.markdown("---")
    st.caption(
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"Total events in DB: {len(events_df)} | "
        f"Showing: {len(filtered_df)} after filters"
    )

except Exception as e:
    st.error(f"Error loading data: {e}")
    import traceback

    with st.expander("Error Details"):
        st.code(traceback.format_exc())
    st.info("Troubleshooting: Check database connection settings in Streamlit Cloud secrets")