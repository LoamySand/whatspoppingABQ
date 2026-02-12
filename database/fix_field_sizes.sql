-- database/fix_field_sizes.sql
-- Increase size limits for text fields

\c event_analytics

-- Increase venue_name size (some are long like "EXPO New Mexico - Home of the State Fair")
ALTER TABLE events ALTER COLUMN venue_name TYPE VARCHAR(255);

-- Increase category size (some have subcategories like "Food, Wine & Beer")
ALTER TABLE events ALTER COLUMN category TYPE VARCHAR(100);

-- Increase cost_description size
ALTER TABLE events ALTER COLUMN cost_description TYPE VARCHAR(255);

-- Increase sponsor size
ALTER TABLE events ALTER COLUMN sponsor TYPE VARCHAR(500);

-- Show updated schema
\d events