\# Database Schema



\## Overview



This directory contains the database schema and utilities for the event analytics pipeline.



\## Database: event\_analytics



PostgreSQL database storing event data and analytics.



\## Tables



\### events



Stores event information scraped from various sources.



| Column | Type | Constraints | Description |

|--------|------|-------------|-------------|

| event\_id | SERIAL | PRIMARY KEY | Auto-incrementing ID |

| event\_name | VARCHAR(255) | NOT NULL | Name of the event |

| venue\_name | VARCHAR(255) | - | Event venue/location |

| event\_date | DATE | NOT NULL | Date of event |

| event\_time | TIME | - | Start time |

| category | VARCHAR(100) | - | Event type (festival, sports, etc.) |

| expected\_attendance | INTEGER | - | Estimated attendance |

| latitude | DECIMAL(10,8) | - | Venue latitude |

| longitude | DECIMAL(11,8) | - | Venue longitude |

| source\_url | TEXT | - | URL of data source |

| created\_at | TIMESTAMP | DEFAULT NOW() | Record creation time |

| updated\_at | TIMESTAMP | DEFAULT NOW() | Last update time |



\*\*Indexes:\*\*

\- `idx\_event\_date` - Query events by date

\- `idx\_category` - Filter by event category

\- `idx\_venue\_name` - Search by venue



\*\*Constraints:\*\*

\- `unique\_event` - Prevents duplicate events (same name + date)



\## Setup

```sql

-- Create database

CREATE DATABASE event\_analytics;



-- Apply schema

\\c event\_analytics

\\i database/schema.sql

```



\## Future Tables



Future sprints will add:

\- `traffic\_data` - Traffic measurements around event venues

\- `reviews` - Business reviews from Yelp, Google

\- `sentiment\_scores` - Processed sentiment analysis results

