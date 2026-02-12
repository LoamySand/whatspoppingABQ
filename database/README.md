# Database Schema



## Overview



This directory contains the database schema and utilities for the event analytics pipeline.



## Database: event_analytics



PostgreSQL database storing event data and analytics.



## Tables



### events



Stores event information scraped from various sources.



| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | SERIAL | PRIMARY KEY | Auto-incrementing ID |
| event_name | VARCHAR(255) | NOT NULL | Name of the event |
| venue_name | VARCHAR(255) | - | Event venue/location |
| event_date | DATE | NOT NULL | Date of event |
| event_time | TIME | - | Start time |
| category | VARCHAR(100) | - | Event type (festival, sports, etc.) |
| expected_attendance | INTEGER | - | Estimated attendance |
| latitude | DECIMAL(10,8) | - | Venue latitude |
| longitude | DECIMAL(11,8) | - | Venue longitude |
| source_url | TEXT | - | URL of data source |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation time |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last update time |


**Indexes:**

- `idx_event_date` - Query events by date

- `idx_category` - Filter by event category

- `idx_venue_name` - Search by venue



**Constraints:**

- `unique_event` - Prevents duplicate events (same name + date)



## Setup

```sql

-- Create database

CREATE DATABASE event_analytics;



-- Apply schema

c event_analytics

i database/schema.sql

```



## Future Tables



Future sprints will add:

- `traffic_data` - Traffic measurements around event venues

- `reviews` - Business reviews from Yelp, Google

- `sentiment_scores` - Processed sentiment analysis results


## Traffic Data Schema (Sprint 2)

### venue_locations

Stores geocoded venue information.

| Column | Type | Description |
|--------|------|-------------|
| venue_id | SERIAL | Primary key |
| venue_name | VARCHAR(255) | Unique venue name |
| address | VARCHAR(500) | Full address |
| latitude | DECIMAL(10,8) | Latitude (WGS84) |
| longitude | DECIMAL(11,8) | Longitude (WGS84) |
| place_id | VARCHAR(255) | Google Place ID |

### traffic_measurements

Stores traffic data collected around venues.

| Column | Type | Description |
|--------|------|-------------|
| measurement_id | SERIAL | Primary key |
| venue_id | INTEGER | FK to venue_locations |
| measurement_time | TIMESTAMP | When measured |
| traffic_level | VARCHAR(50) | light/moderate/heavy/severe |
| avg_speed_mph | DECIMAL(5,2) | Average speed |
| delay_minutes | INTEGER | Delay vs typical |
| data_source | VARCHAR(50) | google_maps, etc. |
| raw_response | JSONB | Full API response |

### Views

**events_with_venues**: Events joined with venue coordinates

**traffic_summary_by_venue**: Aggregated traffic statistics by venue

### Sample Queries
```sql
-- Events with highest traffic impact
SELECT 
    e.event_name,
    AVG(tm.delay_minutes) as avg_delay
FROM events e
JOIN venue_locations v ON e.venue_id = v.venue_id
JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
GROUP BY e.event_id
ORDER BY avg_delay DESC;
```