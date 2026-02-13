-- database/correlation_views.sql
-- SQL views for event-traffic correlation analysis

\c event_analytics

-- View: Events with their traffic measurements
CREATE OR REPLACE VIEW event_traffic_data AS
SELECT 
    e.event_id,
    e.event_name,
    e.event_start_date,
    e.event_start_time,
    e.category,
    v.venue_id,
    v.venue_name,
    tm.measurement_id,
    tm.measurement_time,
    tm.traffic_level,
    tm.delay_minutes,
    tm.avg_speed_mph,
    tm.typical_speed_mph,
    EXTRACT(EPOCH FROM (
        tm.measurement_time - 
        (e.event_start_date + e.event_start_time)
    )) / 3600 AS hours_from_event
FROM events e
JOIN venue_locations v ON e.venue_id = v.venue_id
LEFT JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
WHERE e.event_start_time IS NOT NULL
  AND tm.measurement_time BETWEEN 
      (e.event_start_date + e.event_start_time - INTERVAL '2 hours') AND
      (e.event_start_date + e.event_start_time + INTERVAL '2 hours');

COMMENT ON VIEW event_traffic_data IS 'Events joined with traffic measurements within 2-hour window';

-- View: Event impact summary
CREATE OR REPLACE VIEW event_impact_summary AS
SELECT 
    e.event_id,
    e.event_name,
    e.category,
    v.venue_name,
    COUNT(tm.measurement_id) AS measurement_count,
    AVG(CAST (CASE 
        WHEN tm.measurement_time < (e.event_start_date + e.event_start_time - INTERVAL '30 minutes')
        THEN tm.delay_minutes 
    END AS DECIMAL(9,2))) AS avg_delay_before,
    AVG(CAST (CASE 
        WHEN tm.measurement_time BETWEEN 
            (e.event_start_date + e.event_start_time - INTERVAL '30 minutes') AND
            (e.event_start_date + e.event_start_time + INTERVAL '30 minutes')
        THEN tm.delay_minutes 
    END AS DECIMAL(9,2))) AS avg_delay_during,
    AVG(CAST (CASE 
        WHEN tm.measurement_time > (e.event_start_date + e.event_start_time + INTERVAL '30 minutes')
        THEN tm.delay_minutes 
    END AS DECIMAL(9,2))) AS avg_delay_after
FROM events e
JOIN venue_locations v ON e.venue_id = v.venue_id
LEFT JOIN traffic_measurements tm ON v.venue_id = tm.venue_id
WHERE e.event_start_time IS NOT NULL
  AND tm.measurement_time BETWEEN 
      (e.event_start_date + e.event_start_time - INTERVAL '2 hours') AND
      (e.event_start_date + e.event_start_time + INTERVAL '2 hours')
GROUP BY e.event_id, e.event_name, e.category, v.venue_name;

COMMENT ON VIEW event_impact_summary IS 'Summary of traffic impact before/during/after each event';

-- View: Category impact analysis
CREATE OR REPLACE VIEW category_traffic_impact AS
SELECT 
    category,
    COUNT(DISTINCT event_id) AS event_count,
    AVG(avg_delay_after - avg_delay_before) AS avg_impact_minutes,
    MAX(avg_delay_after - avg_delay_before) AS max_impact_minutes
FROM event_impact_summary
WHERE avg_delay_before IS NOT NULL 
  AND avg_delay_after IS NOT NULL
GROUP BY category
ORDER BY avg_impact_minutes DESC;

COMMENT ON VIEW category_traffic_impact IS 'Average traffic impact by event category';