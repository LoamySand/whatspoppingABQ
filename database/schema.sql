-- database/schema.sql
-- Schema for Albuquerque Event Impact Analytics Pipeline

-- Drop table if exists (for development - allows fresh start)
DROP TABLE IF EXISTS events CASCADE;

-- Events table: stores event data from various sources
CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    venue_name VARCHAR(255),
    event_date DATE NOT NULL,
    event_time TIME,
    category VARCHAR(100),
    expected_attendance INTEGER,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common query patterns
CREATE INDEX idx_event_date ON events(event_date);
CREATE INDEX idx_category ON events(category);
CREATE INDEX idx_venue_name ON events(venue_name);

-- Add unique constraint to prevent duplicate events
-- (same event name on same date = duplicate)
ALTER TABLE events ADD CONSTRAINT unique_event 
UNIQUE (event_name, event_date);

-- Add comments for documentation
COMMENT ON TABLE events IS 'Stores event data scraped from various sources in Albuquerque';
COMMENT ON COLUMN events.event_id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN events.event_name IS 'Name of the event';
COMMENT ON COLUMN events.venue_name IS 'Location where event takes place';
COMMENT ON COLUMN events.event_date IS 'Date of the event';
COMMENT ON COLUMN events.event_time IS 'Start time of the event';
COMMENT ON COLUMN events.category IS 'Event category (festival, concert, sports, etc.)';
COMMENT ON COLUMN events.expected_attendance IS 'Estimated number of attendees';
COMMENT ON COLUMN events.latitude IS 'Venue latitude coordinate';
COMMENT ON COLUMN events.longitude IS 'Venue longitude coordinate';
COMMENT ON COLUMN events.source_url IS 'URL where event data was scraped from';
COMMENT ON COLUMN events.created_at IS 'Timestamp when record was first created';
COMMENT ON COLUMN events.updated_at IS 'Timestamp when record was last updated';