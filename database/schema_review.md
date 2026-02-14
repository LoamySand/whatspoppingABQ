# Database Schema Review - Event Traffic Analytics

## Current Schema Overview

### **Tables**
1. `events` - Event information
2. `venue_locations` - Venue coordinates and details
3. `traffic_measurements` - Traffic data points
4. `events_backup_*` - Backup tables (can be archived)

### **Views**
1. `event_impact_summary` - Event traffic impact aggregation
2. `category_traffic_impact` - Category-level impact analysis
3. `events_with_venues` - Events joined with coordinates
4. `traffic_summary_by_venue` - Venue-level traffic aggregation

---

## Schema Analysis

### ✅ **What's Working Well**

#### 1. **Separation of Concerns**
- Events and venues are properly separated (normalized)
- Traffic measurements are independent of events
- Good use of foreign keys

#### 2. **Geospatial Data**
- Venues have lat/lng coordinates
- Traffic measurements have origin/destination coordinates
- Ready for distance-based analysis

#### 3. **Temporal Data**
- Events have date and time fields
- Traffic measurements have timestamps
- Can correlate by time windows

---

## ⚠️ **Issues & Recommendations**

### **Issue 1: Weak Event-Traffic Linkage**

**Current Problem:**
```
traffic_measurements table has:
- venue_id (link to venue)
- measurement_time (timestamp)
- is_baseline (boolean)

But NO direct link to which EVENT caused the traffic!
```

**Why This is a Problem:**
- You're correlating by time windows in views
- If two events happen at same venue on same day, you can't tell which traffic belongs to which
- Baseline vs event traffic is just a flag, not a relationship

**Recommended Solution:**

Add `event_id` to `traffic_measurements` (nullable):
```sql
ALTER TABLE traffic_measurements
ADD COLUMN event_id INTEGER REFERENCES events(event_id);

CREATE INDEX idx_traffic_event ON traffic_measurements(event_id);

COMMENT ON COLUMN traffic_measurements.event_id IS 
'Event this traffic measurement is associated with (NULL for baseline traffic)';
```

**Benefits:**
- Direct event → traffic link
- Can query "all traffic for event X"
- No ambiguity with overlapping events
- Easier analysis queries

**Migration:**
- Existing data: event_id stays NULL
- New event collections: populate event_id when collecting
- Baseline collections: event_id stays NULL

---

### **Issue 2: Multi-Day Events Complexity**

**Current Schema:**
```sql
events table:
- event_start_date
- event_end_date
- is_multi_day
```

**Problem:**
For a 3-day festival (Feb 15-17), you have ONE event record, but traffic should be collected on ALL 3 days.

**Current Behavior:**
Your correlation logic checks:
```sql
WHERE tm.measurement_time BETWEEN 
    (e.event_start_date + e.event_start_time - INTERVAL '2 hours') AND
    (e.event_start_date + e.event_start_time + INTERVAL '2 hours')
```

This only gets traffic on the FIRST day!

**Recommended Solution:**

**Option A: Event Occurrences Table (Best for analytics)**

Create an `event_occurrences` table:
```sql
CREATE TABLE event_occurrences (
    occurrence_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) NOT NULL,
    occurrence_date DATE NOT NULL,
    occurrence_time TIME,
    is_primary_day BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(event_id, occurrence_date)
);

COMMENT ON TABLE event_occurrences IS 
'Individual occurrences of events (one per day for multi-day events)';
```

**Populate for existing events:**
```sql
-- For single-day events
INSERT INTO event_occurrences (event_id, occurrence_date, occurrence_time)
SELECT event_id, event_start_date, event_start_time
FROM events
WHERE is_multi_day = FALSE OR event_end_date = event_start_date;

-- For multi-day events (generate a row for each day)
INSERT INTO event_occurrences (event_id, occurrence_date, occurrence_time, is_primary_day)
SELECT 
    e.event_id,
    d.occurrence_date,
    e.event_start_time,
    (d.occurrence_date = e.event_start_date) as is_primary_day
FROM events e
CROSS JOIN LATERAL generate_series(
    e.event_start_date,
    e.event_end_date,
    '1 day'::interval
) AS d(occurrence_date)
WHERE e.is_multi_day = TRUE
  AND e.event_end_date > e.event_start_date;
```

**Benefits:**
- Each day of a multi-day event is explicitly represented
- Traffic collection can target specific occurrences
- Analytics can compare Day 1 vs Day 2 vs Day 3 of same event
- Clear relationship: occurrence → traffic measurements

**Update traffic_measurements:**
```sql
ALTER TABLE traffic_measurements
ADD COLUMN occurrence_id INTEGER REFERENCES event_occurrences(occurrence_id);

-- This replaces event_id, or you can keep both
```

**Option B: Simpler - Just improve the correlation logic**

Keep current schema but fix views to handle multi-day:
```sql
-- Match traffic to ANY day of the event
WHERE tm.measurement_time::date BETWEEN e.event_start_date AND e.event_end_date
  AND tm.measurement_time::time BETWEEN 
      (e.event_start_time - INTERVAL '2 hours') AND 
      (e.event_start_time + INTERVAL '2 hours')
```

Less ideal because you can't differentiate between days.

**Recommendation: Use Option A** if you want rich analytics on multi-day events.

---

### **Issue 3: Baseline Traffic Organization**

**Current Approach:**
```
traffic_measurements:
- is_baseline = TRUE/FALSE
- No structure for "what kind of baseline"
```

**Problem:**
All baseline is treated the same. But you have:
- Day of week patterns (Monday vs Saturday)
- Time of day patterns (morning rush vs night)
- Seasonal patterns (summer vs winter)

**Recommended Solution:**

Add baseline metadata:
```sql
ALTER TABLE traffic_measurements
ADD COLUMN baseline_type VARCHAR(50),
ADD COLUMN day_of_week INTEGER,
ADD COLUMN hour_of_day INTEGER;

CREATE INDEX idx_traffic_baseline_type ON traffic_measurements(baseline_type, day_of_week, hour_of_day);

COMMENT ON COLUMN traffic_measurements.baseline_type IS 
'Type of baseline: weekly, monthly, seasonal, or NULL for event traffic';
```

**Populate for existing baseline data:**
```sql
UPDATE traffic_measurements
SET 
    baseline_type = CASE 
        WHEN is_baseline THEN 'weekly'
        ELSE NULL 
    END,
    day_of_week = EXTRACT(DOW FROM measurement_time),
    hour_of_day = EXTRACT(HOUR FROM measurement_time)
WHERE is_baseline = TRUE;
```

**Benefits:**
- Compare event traffic to "same day of week, same time" baseline
- Example: "Saturday 7pm event traffic vs normal Saturday 7pm traffic"
- More accurate impact calculation

---

### **Issue 4: No Event Metadata for Analytics**

**Current Schema:**
```sql
events:
- expected_attendance (estimated, not reliable)
- category (good!)
- sponsor
- cost_min, cost_max
```

**Missing:**
- Actual attendance (if available)
- Event capacity (venue capacity)
- Event type flags (indoor/outdoor, ticketed/free, etc.)
- Weather conditions (could affect traffic)

**Recommended Additions:**
```sql
ALTER TABLE events
ADD COLUMN actual_attendance INTEGER,
ADD COLUMN venue_capacity INTEGER,
ADD COLUMN is_ticketed BOOLEAN DEFAULT TRUE,
ADD COLUMN is_outdoor BOOLEAN DEFAULT FALSE,
ADD COLUMN weather_conditions VARCHAR(50);

COMMENT ON COLUMN events.actual_attendance IS 
'Actual attendance if known (vs expected_attendance estimate)';
```

**Benefits:**
- Correlate traffic impact with actual attendance
- Compare indoor vs outdoor events
- Factor weather into analysis

---

## Proposed Improved Schema

### **Core Tables (Updated)**
```sql
-- Events (master table)
CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    venue_id INTEGER REFERENCES venue_locations(venue_id),
    
    -- Dates
    event_start_date DATE NOT NULL,
    event_end_date DATE NOT NULL,
    is_multi_day BOOLEAN DEFAULT FALSE,
    
    -- Times
    event_start_time TIME,
    event_end_time TIME,
    
    -- Classification
    category VARCHAR(100),
    
    -- Details
    sponsor VARCHAR(500),
    cost_min DECIMAL(10, 2),
    cost_max DECIMAL(10, 2),
    cost_description VARCHAR(255),
    
    -- Attendance
    expected_attendance INTEGER,
    actual_attendance INTEGER,
    venue_capacity INTEGER,
    
    -- Attributes
    is_ticketed BOOLEAN DEFAULT TRUE,
    is_outdoor BOOLEAN DEFAULT FALSE,
    
    -- Contact
    phone VARCHAR(20),
    email VARCHAR(255),
    ticket_url TEXT,
    website_url TEXT,
    
    -- Source
    source_url TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(event_name, event_start_date, venue_name)
);

-- Event Occurrences (NEW - one row per day for multi-day events)
CREATE TABLE event_occurrences (
    occurrence_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) NOT NULL,
    occurrence_date DATE NOT NULL,
    occurrence_time TIME,
    is_primary_day BOOLEAN DEFAULT TRUE,
    
    -- Weather (can be populated later)
    weather_conditions VARCHAR(50),
    temperature_f INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(event_id, occurrence_date)
);

-- Traffic Measurements (UPDATED)
CREATE TABLE traffic_measurements (
    measurement_id SERIAL PRIMARY KEY,
    
    -- Links
    venue_id INTEGER REFERENCES venue_locations(venue_id),
    occurrence_id INTEGER REFERENCES event_occurrences(occurrence_id), -- NEW
    
    -- Timing
    measurement_time TIMESTAMP NOT NULL,
    
    -- Traffic metrics
    traffic_level VARCHAR(50),
    avg_speed_mph DECIMAL(5, 2),
    typical_speed_mph DECIMAL(5, 2),
    travel_time_seconds INTEGER,
    typical_time_seconds INTEGER,
    delay_minutes DECIMAL(6, 2),
    
    -- Location
    origin_lat DECIMAL(10, 8),
    origin_lng DECIMAL(11, 8),
    destination_lat DECIMAL(10, 8),
    destination_lng DECIMAL(11, 8),
    distance_miles DECIMAL(6, 2),
    
    -- Source
    data_source VARCHAR(50) NOT NULL,
    confidence DECIMAL(3, 2),
    raw_response JSONB,
    
    -- Classification
    is_baseline BOOLEAN DEFAULT FALSE,
    baseline_type VARCHAR(50), -- NEW: 'weekly', 'monthly', 'seasonal'
    day_of_week INTEGER, -- NEW: 0=Sunday, 6=Saturday
    hour_of_day INTEGER, -- NEW: 0-23
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_traffic_venue (venue_id),
    INDEX idx_traffic_occurrence (occurrence_id),
    INDEX idx_traffic_time (measurement_time),
    INDEX idx_traffic_baseline (is_baseline, baseline_type, day_of_week, hour_of_day)
);
```

---

## Migration Path

### **Phase 1: Add New Columns (Non-Breaking)**
```sql
-- Add to events
ALTER TABLE events
ADD COLUMN actual_attendance INTEGER,
ADD COLUMN venue_capacity INTEGER,
ADD COLUMN is_ticketed BOOLEAN DEFAULT TRUE,
ADD COLUMN is_outdoor BOOLEAN DEFAULT FALSE,
ADD COLUMN weather_conditions VARCHAR(50);

-- Add to traffic_measurements
ALTER TABLE traffic_measurements
ADD COLUMN baseline_type VARCHAR(50),
ADD COLUMN day_of_week INTEGER,
ADD COLUMN hour_of_day INTEGER;

-- Populate metadata for existing data
UPDATE traffic_measurements
SET 
    day_of_week = EXTRACT(DOW FROM measurement_time),
    hour_of_day = EXTRACT(HOUR FROM measurement_time),
    baseline_type = CASE WHEN is_baseline THEN 'weekly' ELSE NULL END;
```

### **Phase 2: Create Event Occurrences (Breaking - requires code updates)**
```sql
-- Create table
CREATE TABLE event_occurrences (
    occurrence_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) NOT NULL,
    occurrence_date DATE NOT NULL,
    occurrence_time TIME,
    is_primary_day BOOLEAN DEFAULT TRUE,
    weather_conditions VARCHAR(50),
    temperature_f INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, occurrence_date)
);

-- Populate from existing events
-- (SQL from earlier)

-- Add to traffic_measurements
ALTER TABLE traffic_measurements
ADD COLUMN occurrence_id INTEGER REFERENCES event_occurrences(occurrence_id);

-- Create index
CREATE INDEX idx_traffic_occurrence ON traffic_measurements(occurrence_id);
```

### **Phase 3: Update Collection Code**

Update collectors to:
1. Find matching occurrence_id when collecting event traffic
2. Populate occurrence_id in traffic_measurements
3. Use occurrence_id for correlation instead of time windows

---

## Improved Analytics Views

### **Event Impact with Baseline Comparison**
```sql
CREATE OR REPLACE VIEW event_impact_with_baseline AS
SELECT 
    eo.occurrence_id,
    e.event_id,
    e.event_name,
    eo.occurrence_date,
    eo.occurrence_time,
    e.category,
    v.venue_name,
    
    -- Event traffic
    AVG(CASE WHEN tm.occurrence_id IS NOT NULL THEN tm.delay_minutes END) as event_delay,
    COUNT(CASE WHEN tm.occurrence_id IS NOT NULL THEN 1 END) as event_measurements,
    
    -- Baseline traffic (same day of week, same hour)
    AVG(CASE 
        WHEN tm.is_baseline = TRUE 
        AND tm.day_of_week = EXTRACT(DOW FROM eo.occurrence_date)
        AND tm.hour_of_day = EXTRACT(HOUR FROM eo.occurrence_time)
        THEN tm.delay_minutes 
    END) as baseline_delay,
    COUNT(CASE 
        WHEN tm.is_baseline = TRUE 
        AND tm.day_of_week = EXTRACT(DOW FROM eo.occurrence_date)
        AND tm.hour_of_day = EXTRACT(HOUR FROM eo.occurrence_time)
        THEN 1 
    END) as baseline_measurements,
    
    -- Impact calculation
    AVG(CASE WHEN tm.occurrence_id IS NOT NULL THEN tm.delay_minutes END) -
    AVG(CASE 
        WHEN tm.is_baseline = TRUE 
        AND tm.day_of_week = EXTRACT(DOW FROM eo.occurrence_date)
        AND tm.hour_of_day = EXTRACT(HOUR FROM eo.occurrence_time)
        THEN tm.delay_minutes 
    END) as impact_above_baseline

FROM event_occurrences eo
JOIN events e ON eo.event_id = e.event_id
JOIN venue_locations v ON e.venue_id = v.venue_id
LEFT JOIN traffic_measurements tm ON 
    (tm.occurrence_id = eo.occurrence_id OR 
     (tm.is_baseline = TRUE AND tm.venue_id = v.venue_id))
GROUP BY eo.occurrence_id, e.event_id, e.event_name, eo.occurrence_date, 
         eo.occurrence_time, e.category, v.venue_name;
```

This gives you TRUE event impact vs baseline!

---

## Future Extensibility

### **For Business/Review Data**
```sql
-- Business/Venue Reviews (future)
CREATE TABLE venue_reviews (
    review_id SERIAL PRIMARY KEY,
    venue_id INTEGER REFERENCES venue_locations(venue_id),
    review_date DATE,
    rating DECIMAL(2, 1), -- 1.0 to 5.0
    review_text TEXT,
    source VARCHAR(50), -- 'google', 'yelp', etc.
    sentiment_score DECIMAL(3, 2), -- -1.0 to 1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event Sentiment (future)
CREATE TABLE event_sentiment (
    sentiment_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id),
    occurrence_id INTEGER REFERENCES event_occurrences(occurrence_id),
    sentiment_date DATE,
    source VARCHAR(50), -- 'twitter', 'reddit', etc.
    sentiment_score DECIMAL(3, 2),
    mention_count INTEGER,
    positive_mentions INTEGER,
    negative_mentions INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Correlation potential:**
- Do events with high sentiment have worse traffic impact? (people talk about it → more attendees)
- Do venues with better reviews have better traffic flow?
- Does traffic impact correlate with negative sentiment afterward?

---

## Recommendations Priority

### **High Priority (Do Now)**
1. ✅ Add `day_of_week` and `hour_of_day` to traffic_measurements
2. ✅ Add `baseline_type` to traffic_measurements  
3. ✅ Populate metadata for existing data

### **Medium Priority (Do Soon)**
4. 🟡 Create `event_occurrences` table
5. 🟡 Add `occurrence_id` to traffic_measurements
6. 🟡 Update collectors to use occurrence_id

### **Low Priority (Future)**
7. ⚪ Add attendance/capacity fields to events
8. ⚪ Add weather tracking
9. ⚪ Create review/sentiment tables

---

## Next Steps

1. **Review this document** - Does this schema make sense for your analytics goals?
2. **Apply Phase 1 migrations** - Add columns (non-breaking)
3. **Update views** - Use new baseline comparison logic
4. **Test analytics** - Verify better correlation
5. **Plan Phase 2** - Event occurrences (breaking change)

Would you like me to create the migration SQL scripts?