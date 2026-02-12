-- database/schema_traffic.sql
-- Traffic data schema for Sprint 2
-- Adds venue locations and traffic measurements

-- ============================================================
-- VENUE LOCATIONS TABLE
-- ============================================================
-- Stores geocoded venue information with coordinates

CREATE TABLE IF NOT EXISTS venue_locations (
    venue_id SERIAL PRIMARY KEY,
    venue_name VARCHAR(255) UNIQUE NOT NULL,
    address VARCHAR(500),
    city VARCHAR(100) DEFAULT 'Albuquerque',
    state VARCHAR(2) DEFAULT 'NM',
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    place_id VARCHAR(255),  -- Google Places ID for reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for venue lookups
CREATE INDEX idx_venue_name ON venue_locations(venue_name);
CREATE INDEX idx_venue_coords ON venue_locations(latitude, longitude);

-- Comments
COMMENT ON TABLE venue_locations IS 'Geocoded venue locations with coordinates';
COMMENT ON COLUMN venue_locations.venue_id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN venue_locations.venue_name IS 'Venue name (unique)';
COMMENT ON COLUMN venue_locations.latitude IS 'Latitude coordinate (WGS84)';
COMMENT ON COLUMN venue_locations.longitude IS 'Longitude coordinate (WGS84)';
COMMENT ON COLUMN venue_locations.place_id IS 'Google Places ID for API reference';

-- ============================================================
-- TRAFFIC MEASUREMENTS TABLE
-- ============================================================
-- Stores traffic data collected around venues

CREATE TABLE IF NOT EXISTS traffic_measurements (
    measurement_id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venue_locations(venue_id) ON DELETE CASCADE,
    measurement_time TIMESTAMP NOT NULL,
    
    -- Traffic metrics
    traffic_level VARCHAR(50),          -- 'light', 'moderate', 'heavy', 'severe'
    avg_speed_mph DECIMAL(5, 2),        -- Average speed in mph
    typical_speed_mph DECIMAL(5, 2),    -- Typical speed for this time/day
    travel_time_seconds INTEGER,        -- Actual travel time
    typical_time_seconds INTEGER,       -- Typical travel time
    delay_minutes INTEGER,              -- Delay vs typical (can be negative)
    
    -- Metadata
    data_source VARCHAR(50) NOT NULL,   -- 'google_maps'
    origin_lat DECIMAL(10, 8),          -- Where measurement started
    origin_lng DECIMAL(11, 8),
    destination_lat DECIMAL(10, 8),     -- Where measurement ended
    destination_lng DECIMAL(11, 8),
    distance_miles DECIMAL(6, 2),       -- Distance measured
    
    -- Raw data storage (for debugging/reprocessing)
    raw_response JSONB,                 -- Full API response
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX idx_traffic_venue ON traffic_measurements(venue_id);
CREATE INDEX idx_traffic_time ON traffic_measurements(measurement_time);
CREATE INDEX idx_traffic_venue_time ON traffic_measurements(venue_id, measurement_time DESC);
CREATE INDEX idx_traffic_level ON traffic_measurements(traffic_level);

-- Comments
COMMENT ON TABLE traffic_measurements IS 'Traffic measurements collected around event venues';
COMMENT ON COLUMN traffic_measurements.measurement_time IS 'When traffic was measured (UTC)';
COMMENT ON COLUMN traffic_measurements.traffic_level IS 'Qualitative traffic assessment';
COMMENT ON COLUMN traffic_measurements.delay_minutes IS 'Delay compared to typical conditions';
COMMENT ON COLUMN traffic_measurements.raw_response IS 'Full API response for debugging';

-- ============================================================
-- UPDATE EVENTS TABLE
-- ============================================================
-- Link events to venues

ALTER TABLE events 
ADD COLUMN IF NOT EXISTS venue_id INTEGER REFERENCES venue_locations(venue_id);

-- Index for event-venue joins
CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id);

COMMENT ON COLUMN events.venue_id IS 'Foreign key to venue_locations table';

-- ============================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================

-- View: Events with venue coordinates
CREATE OR REPLACE VIEW events_with_venues AS
SELECT 
    e.event_id,
    e.event_name,
    e.event_date,
    e.event_time,
    e.category,
    e.venue_name,
    v.venue_id,
    v.latitude,
    v.longitude,
    v.address
FROM events e
LEFT JOIN venue_locations v ON e.venue_id = v.venue_id;

COMMENT ON VIEW events_with_venues IS 'Events joined with venue location data';

-- View: Traffic summary by venue
CREATE OR REPLACE VIEW traffic_summary_by_venue AS
SELECT 
    v.venue_id,
    v.venue_name,
    COUNT(tm.measurement_id) as measurement_count,
    AVG(tm.delay_minutes) as avg_delay_minutes,
    MAX(tm.delay_minutes) as max_delay_minutes,
    MIN(tm.measurement_time) as first_measurement,
    MAX(tm.measurement_time) as last_measurement
FROM venue_locations v
LEFT JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
GROUP BY v.venue_id, v.venue_name;

COMMENT ON VIEW traffic_summary_by_venue IS 'Summary statistics of traffic by venue';

-- ============================================================
-- SAMPLE QUERIES (for reference)
-- ============================================================

-- Example: Get traffic during an event
/*
SELECT 
    e.event_name,
    e.event_date,
    tm.measurement_time,
    tm.traffic_level,
    tm.delay_minutes
FROM events e
JOIN venue_locations v ON e.venue_id = v.venue_id
JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
WHERE e.event_id = 1
  AND tm.measurement_time BETWEEN 
      e.event_date + e.event_time - INTERVAL '2 hours' AND
      e.event_date + e.event_time + INTERVAL '3 hours'
ORDER BY tm.measurement_time;
*/

-- Example: Events with highest traffic impact
/*
SELECT 
    e.event_name,
    e.event_date,
    v.venue_name,
    AVG(tm.delay_minutes) as avg_delay,
    MAX(tm.delay_minutes) as max_delay
FROM events e
JOIN venue_locations v ON e.venue_id = v.venue_id
JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
WHERE tm.measurement_time BETWEEN 
    e.event_date + COALESCE(e.event_time, '18:00:00'::TIME) - INTERVAL '1 hour' AND
    e.event_date + COALESCE(e.event_time, '18:00:00'::TIME) + INTERVAL '4 hours'
GROUP BY e.event_id, e.event_name, e.event_date, v.venue_name
HAVING AVG(tm.delay_minutes) > 0
ORDER BY avg_delay DESC
LIMIT 10;
*/