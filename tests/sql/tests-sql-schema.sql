-- Test-database schema, mirroring production's `app` schema.
-- Kept intentionally separate from database/schema/event_analytics_schema.sql,
-- which is stale (uses `public`, not `app` — see SCRUM-16 test suite notes).

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE app.venue_locations (
    venue_id serial PRIMARY KEY,
    venue_name character varying NOT NULL UNIQUE,
    address character varying,
    city character varying DEFAULT 'Albuquerque',
    state character varying DEFAULT 'NM',
    latitude numeric NOT NULL,
    longitude numeric NOT NULL,
    place_id character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app.events (
    event_id serial PRIMARY KEY,
    event_name character varying NOT NULL,
    venue_name character varying,
    category character varying,
    expected_attendance integer,
    latitude numeric,
    longitude numeric,
    source_url text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    venue_id integer REFERENCES app.venue_locations(venue_id),
    event_start_date date,
    event_end_date date,
    event_start_time time without time zone,
    event_end_time time without time zone,
    is_multi_day boolean DEFAULT false,
    sponsor character varying,
    cost_min numeric,
    cost_max numeric,
    cost_description character varying,
    phone character varying,
    email character varying,
    ticket_url text,
    website_url text
);

CREATE TABLE app.traffic_measurements (
    measurement_id serial PRIMARY KEY,
    venue_id integer REFERENCES app.venue_locations(venue_id),
    measurement_time timestamp without time zone NOT NULL,
    traffic_level character varying,
    avg_speed_mph numeric,
    typical_speed_mph numeric,
    travel_time_seconds integer,
    typical_time_seconds integer,
    delay_minutes integer,
    data_source character varying NOT NULL,
    origin_lat numeric,
    origin_lng numeric,
    destination_lat numeric,
    destination_lng numeric,
    distance_miles numeric,
    raw_response jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    event_id integer REFERENCES app.events(event_id),
    is_baseline boolean,
    baseline_type character varying,
    day_of_week integer,
    hour_of_day integer
);