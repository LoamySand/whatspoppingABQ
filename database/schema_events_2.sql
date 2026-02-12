-- database/schema_events_v2.sql
-- Enhanced event schema with multi-day support and detailed information

-- Update events table with new fields
ALTER TABLE events 
    DROP COLUMN IF EXISTS event_date CASCADE,
    DROP COLUMN IF EXISTS event_time CASCADE;

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS event_start_date DATE,
    ADD COLUMN IF NOT EXISTS event_end_date DATE,
    ADD COLUMN IF NOT EXISTS event_start_time TIME,
    ADD COLUMN IF NOT EXISTS event_end_time TIME,
    ADD COLUMN IF NOT EXISTS is_multi_day BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sponsor VARCHAR(255),
    ADD COLUMN IF NOT EXISTS cost_min DECIMAL(10, 2),
    ADD COLUMN IF NOT EXISTS cost_max DECIMAL(10, 2),
    ADD COLUMN IF NOT EXISTS cost_description VARCHAR(100),
    ADD COLUMN IF NOT EXISTS phone VARCHAR(20),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS ticket_url TEXT,
    ADD COLUMN IF NOT EXISTS website_url TEXT;

-- Update indexes
DROP INDEX IF EXISTS idx_event_date;
CREATE INDEX idx_event_start_date ON events(event_start_date);
CREATE INDEX idx_event_end_date ON events(event_end_date);
CREATE INDEX idx_event_date_range ON events(event_start_date, event_end_date);

-- Update unique constraint
ALTER TABLE events DROP CONSTRAINT IF EXISTS unique_event;
ALTER TABLE events DROP CONSTRAINT IF EXISTS unique_event_source;
ALTER TABLE events ADD CONSTRAINT unique_event_enhanced 
    UNIQUE (event_name, event_start_date, venue_name);

-- Add comments
COMMENT ON COLUMN events.event_start_date IS 'First day of event';
COMMENT ON COLUMN events.event_end_date IS 'Last day of event (same as start_date for single-day)';
COMMENT ON COLUMN events.event_start_time IS 'Event start time';
COMMENT ON COLUMN events.event_end_time IS 'Event end time';
COMMENT ON COLUMN events.is_multi_day IS 'True if event spans multiple days';
COMMENT ON COLUMN events.sponsor IS 'Event sponsor/presenter';
COMMENT ON COLUMN events.cost_min IS 'Minimum ticket price';
COMMENT ON COLUMN events.cost_max IS 'Maximum ticket price';
COMMENT ON COLUMN events.cost_description IS 'Cost description (e.g., "Free", "$50-$100")';
COMMENT ON COLUMN events.phone IS 'Contact phone number';
COMMENT ON COLUMN events.email IS 'Contact email';
COMMENT ON COLUMN events.ticket_url IS 'URL to purchase tickets';
COMMENT ON COLUMN events.website_url IS 'Event or organizer website';

-- Create view for single-day events (backward compatibility)
CREATE OR REPLACE VIEW events_single_day AS
SELECT 
    event_id,
    event_name,
    venue_name,
    event_start_date as event_date,
    event_start_time as event_time,
    category,
    venue_id,
    created_at,
    updated_at
FROM events
WHERE is_multi_day = FALSE OR event_start_date = event_end_date;

-- Create view for multi-day events
CREATE OR REPLACE VIEW events_multi_day AS
SELECT 
    event_id,
    event_name,
    venue_name,
    event_start_date,
    event_end_date,
    event_start_time,
    event_end_time,
    category,
    venue_id,
    (event_end_date - event_start_date + 1) as duration_days
FROM events
WHERE is_multi_day = TRUE AND event_start_date != event_end_date;

COMMENT ON VIEW events_single_day IS 'Events occurring on a single day';
COMMENT ON VIEW events_multi_day IS 'Events spanning multiple days';