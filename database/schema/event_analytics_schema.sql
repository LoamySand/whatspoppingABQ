--
-- PostgreSQL database dump
--

\restrict tmsC25Sl3G1fzAOMWIPy0qsU6y0gk3AjYh2DJN16xh7Zo5vWvICVC9LCqpgKBPf

-- Dumped from database version 17.7
-- Dumped by pg_dump version 17.7

-- Started on 2026-02-15 15:35:17

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 16987)
-- Name: traffic_measurements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.traffic_measurements (
    measurement_id integer NOT NULL,
    venue_id integer,
    measurement_time timestamp without time zone NOT NULL,
    traffic_level character varying(50),
    avg_speed_mph numeric(5,2),
    typical_speed_mph numeric(5,2),
    travel_time_seconds integer,
    typical_time_seconds integer,
    delay_minutes integer,
    data_source character varying(50) NOT NULL,
    origin_lat numeric(10,8),
    origin_lng numeric(11,8),
    destination_lat numeric(10,8),
    destination_lng numeric(11,8),
    distance_miles numeric(6,2),
    raw_response jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    event_id integer,
    is_baseline boolean,
    baseline_type character varying(50),
    day_of_week integer,
    hour_of_day integer
);


ALTER TABLE public.traffic_measurements OWNER TO postgres;

--
-- TOC entry 5006 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE traffic_measurements; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.traffic_measurements IS 'Traffic measurements collected around event venues';


--
-- TOC entry 5007 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN traffic_measurements.measurement_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.traffic_measurements.measurement_time IS 'When traffic was measured (UTC)';


--
-- TOC entry 5008 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN traffic_measurements.traffic_level; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.traffic_measurements.traffic_level IS 'Qualitative traffic assessment';


--
-- TOC entry 5009 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN traffic_measurements.delay_minutes; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.traffic_measurements.delay_minutes IS 'Delay compared to typical conditions';


--
-- TOC entry 5010 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN traffic_measurements.raw_response; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.traffic_measurements.raw_response IS 'Full API response for debugging';


--
-- TOC entry 5011 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN traffic_measurements.event_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.traffic_measurements.event_id IS 'Event this traffic measurement is associated with (NULL for baseline traffic)';


--
-- TOC entry 5012 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN traffic_measurements.baseline_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.traffic_measurements.baseline_type IS 'Type of baseline: weekly, monthly, seasonal, or NULL for event traffic';


--
-- TOC entry 235 (class 1259 OID 17413)
-- Name: api_usage_by_day; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.api_usage_by_day AS
 SELECT date(measurement_time) AS date,
    data_source,
    count(*) AS api_calls,
    count(
        CASE
            WHEN (is_baseline = true) THEN 1
            ELSE NULL::integer
        END) AS baseline_calls,
    count(
        CASE
            WHEN (event_id IS NOT NULL) THEN 1
            ELSE NULL::integer
        END) AS event_calls,
        CASE
            WHEN ((data_source)::text = 'google_maps'::text) THEN count(*)
            ELSE (0)::bigint
        END AS google_maps_calls,
        CASE
            WHEN ((data_source)::text = 'tomtom'::text) THEN count(*)
            ELSE (0)::bigint
        END AS tomtom_calls,
    min(measurement_time) AS first_call,
    max(measurement_time) AS last_call
   FROM public.traffic_measurements
  WHERE (measurement_time >= (CURRENT_DATE - 30))
  GROUP BY (date(measurement_time)), data_source
  ORDER BY (date(measurement_time)) DESC, data_source;


ALTER VIEW public.api_usage_by_day OWNER TO postgres;

--
-- TOC entry 5014 (class 0 OID 0)
-- Dependencies: 235
-- Name: VIEW api_usage_by_day; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.api_usage_by_day IS 'Daily API usage and cost tracking for last 30 days';


--
-- TOC entry 218 (class 1259 OID 16952)
-- Name: events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.events (
    event_id integer NOT NULL,
    event_name character varying(255) NOT NULL,
    venue_name character varying(255),
    category character varying(100),
    expected_attendance integer,
    latitude numeric(10,8),
    longitude numeric(11,8),
    source_url text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    venue_id integer,
    event_start_date date,
    event_end_date date,
    event_start_time time without time zone,
    event_end_time time without time zone,
    is_multi_day boolean DEFAULT false,
    sponsor character varying(500),
    cost_min numeric(10,2),
    cost_max numeric(10,2),
    cost_description character varying(255),
    phone character varying(20),
    email character varying(255),
    ticket_url text,
    website_url text
);


ALTER TABLE public.events OWNER TO postgres;

--
-- TOC entry 5016 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE events; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.events IS 'Stores event data scraped from various sources in Albuquerque';


--
-- TOC entry 5017 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.event_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.event_id IS 'Auto-incrementing primary key';


--
-- TOC entry 5018 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.event_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.event_name IS 'Name of the event';


--
-- TOC entry 5019 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.venue_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.venue_name IS 'Location where event takes place';


--
-- TOC entry 5020 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.category; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.category IS 'Event category (festival, concert, sports, etc.)';


--
-- TOC entry 5021 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.expected_attendance; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.expected_attendance IS 'Estimated number of attendees';


--
-- TOC entry 5022 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.latitude; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.latitude IS 'Venue latitude coordinate';


--
-- TOC entry 5023 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.longitude; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.longitude IS 'Venue longitude coordinate';


--
-- TOC entry 5024 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.source_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.source_url IS 'URL where event data was scraped from';


--
-- TOC entry 5025 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.created_at IS 'Timestamp when record was first created';


--
-- TOC entry 5026 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.updated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.updated_at IS 'Timestamp when record was last updated';


--
-- TOC entry 5027 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.venue_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.venue_id IS 'Foreign key to venue_locations table';


--
-- TOC entry 5028 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.event_start_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.event_start_date IS 'First day of event';


--
-- TOC entry 5029 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.event_end_date; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.event_end_date IS 'Last day of event (same as start_date for single-day)';


--
-- TOC entry 5030 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.event_start_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.event_start_time IS 'Event start time';


--
-- TOC entry 5031 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.event_end_time; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.event_end_time IS 'Event end time';


--
-- TOC entry 5032 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.is_multi_day; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.is_multi_day IS 'True if event spans multiple days';


--
-- TOC entry 5033 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.sponsor; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.sponsor IS 'Event sponsor/presenter';


--
-- TOC entry 5034 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.cost_min; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.cost_min IS 'Minimum ticket price';


--
-- TOC entry 5035 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.cost_max; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.cost_max IS 'Maximum ticket price';


--
-- TOC entry 5036 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.cost_description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.cost_description IS 'Cost description (e.g., "Free", "$50-$100")';


--
-- TOC entry 5037 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.phone; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.phone IS 'Contact phone number';


--
-- TOC entry 5038 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.email; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.email IS 'Contact email';


--
-- TOC entry 5039 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.ticket_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.ticket_url IS 'URL to purchase tickets';


--
-- TOC entry 5040 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN events.website_url; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.events.website_url IS 'Event or organizer website';


--
-- TOC entry 220 (class 1259 OID 16971)
-- Name: venue_locations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.venue_locations (
    venue_id integer NOT NULL,
    venue_name character varying(255) NOT NULL,
    address character varying(500),
    city character varying(100) DEFAULT 'Albuquerque'::character varying,
    state character varying(2) DEFAULT 'NM'::character varying,
    latitude numeric(10,8) NOT NULL,
    longitude numeric(11,8) NOT NULL,
    place_id character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.venue_locations OWNER TO postgres;

--
-- TOC entry 5042 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE venue_locations; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.venue_locations IS 'Geocoded venue locations with coordinates';


--
-- TOC entry 5043 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN venue_locations.venue_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.venue_locations.venue_id IS 'Auto-incrementing primary key';


--
-- TOC entry 5044 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN venue_locations.venue_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.venue_locations.venue_name IS 'Venue name (unique)';


--
-- TOC entry 5045 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN venue_locations.latitude; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.venue_locations.latitude IS 'Latitude coordinate (WGS84)';


--
-- TOC entry 5046 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN venue_locations.longitude; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.venue_locations.longitude IS 'Longitude coordinate (WGS84)';


--
-- TOC entry 5047 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN venue_locations.place_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.venue_locations.place_id IS 'Google Places ID for API reference';


--
-- TOC entry 237 (class 1259 OID 17685)
-- Name: event_traffic_with_baseline; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.event_traffic_with_baseline AS
 SELECT e.event_id,
    e.event_name,
    e.event_start_date,
    e.event_start_time,
    e.category,
    e.is_multi_day,
    v.venue_id,
    v.venue_name,
    v.latitude,
    v.longitude,
    count(
        CASE
            WHEN (tm.event_id IS NOT NULL) THEN 1
            ELSE NULL::integer
        END) AS event_measurements,
    avg(
        CASE
            WHEN (tm.event_id IS NOT NULL) THEN tm.delay_minutes
            ELSE NULL::integer
        END) AS event_avg_delay,
    max(
        CASE
            WHEN (tm.event_id IS NOT NULL) THEN tm.delay_minutes
            ELSE NULL::integer
        END) AS event_max_delay,
    avg(
        CASE
            WHEN (tm.event_id IS NOT NULL) THEN tm.avg_speed_mph
            ELSE NULL::numeric
        END) AS event_avg_speed,
    count(
        CASE
            WHEN ((tm.is_baseline = true) AND ((tm.day_of_week)::numeric = EXTRACT(dow FROM e.event_start_date)) AND ((tm.hour_of_day)::numeric = EXTRACT(hour FROM e.event_start_time)) AND (tm.venue_id = v.venue_id)) THEN 1
            WHEN ((tm.is_baseline = true) AND (((tm.day_of_week)::numeric = EXTRACT(dow FROM e.event_start_date)) OR ((tm.hour_of_day)::numeric = EXTRACT(hour FROM e.event_start_time))) AND (tm.venue_id = v.venue_id)) THEN 1
            ELSE NULL::integer
        END) AS baseline_measurements,
    avg(
        CASE
            WHEN ((tm.is_baseline = true) AND ((tm.day_of_week)::numeric = EXTRACT(dow FROM e.event_start_date)) AND ((tm.hour_of_day)::numeric = EXTRACT(hour FROM e.event_start_time)) AND (tm.venue_id = v.venue_id)) THEN tm.delay_minutes
            ELSE NULL::integer
        END) AS baseline_avg_delay,
    avg(
        CASE
            WHEN ((tm.is_baseline = true) AND ((tm.day_of_week)::numeric = EXTRACT(dow FROM e.event_start_date)) AND ((tm.hour_of_day)::numeric = EXTRACT(hour FROM e.event_start_time)) AND (tm.venue_id = v.venue_id)) THEN tm.avg_speed_mph
            ELSE NULL::numeric
        END) AS baseline_avg_speed,
    (avg(
        CASE
            WHEN (tm.event_id IS NOT NULL) THEN tm.delay_minutes
            ELSE NULL::integer
        END) - avg(
        CASE
            WHEN ((tm.is_baseline = true) AND ((tm.day_of_week)::numeric = EXTRACT(dow FROM e.event_start_date)) AND ((tm.hour_of_day)::numeric = EXTRACT(hour FROM e.event_start_time)) AND (tm.venue_id = v.venue_id)) THEN tm.delay_minutes
            ELSE NULL::integer
        END)) AS impact_above_baseline
   FROM ((public.events e
     JOIN public.venue_locations v ON ((e.venue_id = v.venue_id)))
     LEFT JOIN public.traffic_measurements tm ON (((tm.event_id = e.event_id) OR ((tm.is_baseline = true) AND (tm.venue_id = v.venue_id)))))
  WHERE (e.event_start_time IS NOT NULL)
  GROUP BY e.event_id, e.event_name, e.event_start_date, e.event_start_time, e.category, e.is_multi_day, v.venue_id, v.venue_name, v.latitude, v.longitude;


ALTER VIEW public.event_traffic_with_baseline OWNER TO postgres;

--
-- TOC entry 5049 (class 0 OID 0)
-- Dependencies: 237
-- Name: VIEW event_traffic_with_baseline; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.event_traffic_with_baseline IS 'Event traffic metrics compared to baseline traffic from same day-of-week and hour';


--
-- TOC entry 239 (class 1259 OID 17695)
-- Name: category_traffic_impact; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.category_traffic_impact AS
 SELECT category,
    count(DISTINCT event_id) AS event_count,
    count(DISTINCT
        CASE
            WHEN (impact_above_baseline IS NOT NULL) THEN event_id
            ELSE NULL::integer
        END) AS events_with_baseline,
    avg(impact_above_baseline) AS avg_impact_minutes,
    max(impact_above_baseline) AS max_impact_minutes,
    min(impact_above_baseline) AS min_impact_minutes,
    avg(event_avg_delay) AS avg_event_delay,
    avg(baseline_avg_delay) AS avg_baseline_delay,
    round(((100.0 * (count(
        CASE
            WHEN (impact_above_baseline > (2)::numeric) THEN 1
            ELSE NULL::integer
        END))::numeric) / (NULLIF(count(DISTINCT event_id), 0))::numeric), 1) AS pct_high_impact
   FROM public.event_traffic_with_baseline
  WHERE (event_measurements > 0)
  GROUP BY category
  ORDER BY (avg(impact_above_baseline)) DESC NULLS LAST;


ALTER VIEW public.category_traffic_impact OWNER TO postgres;

--
-- TOC entry 5050 (class 0 OID 0)
-- Dependencies: 239
-- Name: VIEW category_traffic_impact; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.category_traffic_impact IS 'Traffic impact statistics by event category';


--
-- TOC entry 234 (class 1259 OID 17408)
-- Name: collection_schedule_validation; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.collection_schedule_validation AS
 WITH upcoming_events AS (
         SELECT e.event_id,
            e.event_name,
            e.event_start_date,
            e.event_start_time,
            (e.event_start_date + e.event_start_time) AS event_datetime
           FROM public.events e
          WHERE ((e.event_start_time IS NOT NULL) AND ((e.event_start_date >= (CURRENT_DATE - 1)) AND (e.event_start_date <= (CURRENT_DATE + 1))))
        )
 SELECT ue.event_id,
    ue.event_name,
    ue.event_datetime,
    (ue.event_datetime - '02:00:00'::interval) AS collection_window_start,
    (ue.event_datetime + '02:00:00'::interval) AS collection_window_end,
    count(tm.measurement_id) AS actual_measurements,
    min(tm.measurement_time) AS first_measurement,
    max(tm.measurement_time) AS last_measurement,
        CASE
            WHEN (count(tm.measurement_id) = 0) THEN 'No data collected'::text
            WHEN (count(tm.measurement_id) < 9) THEN 'Incomplete collection'::text
            WHEN (count(tm.measurement_id) >= 9) THEN 'Good coverage'::text
            ELSE 'Unknown'::text
        END AS collection_status,
    (EXTRACT(epoch FROM ((ue.event_datetime)::timestamp with time zone - now())) / (3600)::numeric) AS hours_until_event
   FROM (upcoming_events ue
     LEFT JOIN public.traffic_measurements tm ON ((ue.event_id = tm.event_id)))
  GROUP BY ue.event_id, ue.event_name, ue.event_datetime
  ORDER BY ue.event_datetime;


ALTER VIEW public.collection_schedule_validation OWNER TO postgres;

--
-- TOC entry 5051 (class 0 OID 0)
-- Dependencies: 234
-- Name: VIEW collection_schedule_validation; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.collection_schedule_validation IS 'Validates traffic collection for events happening soon';


--
-- TOC entry 229 (class 1259 OID 17383)
-- Name: collection_status_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.collection_status_summary AS
 SELECT ( SELECT count(*) AS count
           FROM public.events) AS total_events,
    ( SELECT count(*) AS count
           FROM public.events
          WHERE (events.event_start_time IS NOT NULL)) AS events_with_time,
    ( SELECT count(*) AS count
           FROM public.venue_locations) AS total_venues,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements) AS total_measurements,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE (traffic_measurements.event_id IS NOT NULL)) AS event_measurements,
    ( SELECT count(DISTINCT traffic_measurements.event_id) AS count
           FROM public.traffic_measurements
          WHERE (traffic_measurements.event_id IS NOT NULL)) AS events_with_traffic,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE (traffic_measurements.is_baseline = true)) AS baseline_measurements,
    ( SELECT count(DISTINCT traffic_measurements.venue_id) AS count
           FROM public.traffic_measurements
          WHERE (traffic_measurements.is_baseline = true)) AS venues_with_baseline,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE (traffic_measurements.measurement_time > (now() - '24:00:00'::interval))) AS measurements_last_24h,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE ((traffic_measurements.measurement_time > (now() - '24:00:00'::interval)) AND (traffic_measurements.is_baseline = true))) AS baseline_last_24h,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE ((traffic_measurements.measurement_time > (now() - '24:00:00'::interval)) AND (traffic_measurements.event_id IS NOT NULL))) AS event_traffic_last_24h,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE ((traffic_measurements.data_source)::text = 'google_maps'::text)) AS google_maps_calls,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE ((traffic_measurements.data_source)::text = 'tomtom'::text)) AS tomtom_calls,
    ( SELECT max(traffic_measurements.measurement_time) AS max
           FROM public.traffic_measurements) AS last_measurement,
    ( SELECT max(traffic_measurements.measurement_time) AS max
           FROM public.traffic_measurements
          WHERE (traffic_measurements.is_baseline = true)) AS last_baseline_collection,
    ( SELECT max(traffic_measurements.measurement_time) AS max
           FROM public.traffic_measurements
          WHERE (traffic_measurements.event_id IS NOT NULL)) AS last_event_collection;


ALTER VIEW public.collection_status_summary OWNER TO postgres;

--
-- TOC entry 5053 (class 0 OID 0)
-- Dependencies: 229
-- Name: VIEW collection_status_summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.collection_status_summary IS 'High-level summary of data collection status';


--
-- TOC entry 233 (class 1259 OID 17403)
-- Name: data_quality_check; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.data_quality_check AS
 SELECT 'Events without times'::text AS issue,
    count(*) AS count,
    'Events need event_start_time for collection'::text AS impact
   FROM public.events
  WHERE (events.event_start_time IS NULL)
UNION ALL
 SELECT 'Events without venue'::text AS issue,
    count(*) AS count,
    'Events need venue_id for geocoding'::text AS impact
   FROM public.events
  WHERE (events.venue_id IS NULL)
UNION ALL
 SELECT 'Venues without coordinates'::text AS issue,
    count(*) AS count,
    'Venues need lat/lng for traffic collection'::text AS impact
   FROM public.venue_locations
  WHERE ((venue_locations.latitude IS NULL) OR (venue_locations.longitude IS NULL))
UNION ALL
 SELECT 'Traffic without event or baseline flag'::text AS issue,
    count(*) AS count,
    'Measurements should have event_id OR is_baseline=TRUE'::text AS impact
   FROM public.traffic_measurements
  WHERE ((traffic_measurements.event_id IS NULL) AND (traffic_measurements.is_baseline = false))
UNION ALL
 SELECT 'Traffic missing day_of_week'::text AS issue,
    count(*) AS count,
    'Should be auto-calculated'::text AS impact
   FROM public.traffic_measurements
  WHERE (traffic_measurements.day_of_week IS NULL)
UNION ALL
 SELECT 'Traffic missing hour_of_day'::text AS issue,
    count(*) AS count,
    'Should be auto-calculated'::text AS impact
   FROM public.traffic_measurements
  WHERE (traffic_measurements.hour_of_day IS NULL)
UNION ALL
 SELECT 'Baseline without baseline_type'::text AS issue,
    count(*) AS count,
    'Baseline should have type (weekly/monthly)'::text AS impact
   FROM public.traffic_measurements
  WHERE ((traffic_measurements.is_baseline = true) AND (traffic_measurements.baseline_type IS NULL))
  ORDER BY 2 DESC;


ALTER VIEW public.data_quality_check OWNER TO postgres;

--
-- TOC entry 5055 (class 0 OID 0)
-- Dependencies: 233
-- Name: VIEW data_quality_check; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.data_quality_check IS 'Identifies data quality issues across all tables';


--
-- TOC entry 240 (class 1259 OID 17713)
-- Name: event_impact_detail; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.event_impact_detail AS
 SELECT e.event_id,
    e.event_name,
    e.event_start_date,
    e.event_start_time,
    e.event_end_date,
    e.category,
    e.sponsor,
    e.cost_description,
    e.is_multi_day,
    v.venue_id,
    v.venue_name,
    v.latitude,
    v.longitude,
    etb.event_measurements,
    etb.baseline_measurements,
    etb.event_avg_delay,
    etb.baseline_avg_delay,
    etb.event_avg_speed,
    etb.baseline_avg_speed,
    etb.event_max_delay,
    etb.impact_above_baseline,
        CASE
            WHEN (etb.impact_above_baseline IS NULL) THEN 'unknown'::text
            WHEN (etb.impact_above_baseline > (5)::numeric) THEN 'severe'::text
            WHEN (etb.impact_above_baseline > (2)::numeric) THEN 'high'::text
            WHEN (etb.impact_above_baseline > (1)::numeric) THEN 'moderate'::text
            WHEN (etb.impact_above_baseline > (0)::numeric) THEN 'low'::text
            ELSE 'none'::text
        END AS impact_level,
        CASE
            WHEN (etb.event_measurements = 0) THEN 'no_event_data'::text
            WHEN (etb.baseline_measurements = 0) THEN 'no_baseline_data'::text
            WHEN ((etb.baseline_measurements > 0) AND (etb.event_measurements > 0)) THEN 'complete'::text
            WHEN ((etb.baseline_measurements > 0) OR (etb.event_measurements > 0)) THEN 'partial'::text
            ELSE 'unknown'::text
        END AS data_quality
   FROM ((public.events e
     JOIN public.venue_locations v ON ((e.venue_id = v.venue_id)))
     LEFT JOIN public.event_traffic_with_baseline etb ON ((e.event_id = etb.event_id)))
  WHERE (e.event_start_time IS NOT NULL)
  ORDER BY e.event_start_date DESC, e.event_start_time DESC;


ALTER VIEW public.event_impact_detail OWNER TO postgres;

--
-- TOC entry 5057 (class 0 OID 0)
-- Dependencies: 240
-- Name: VIEW event_impact_detail; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.event_impact_detail IS 'Comprehensive event impact with baseline match quality indicators';


--
-- TOC entry 238 (class 1259 OID 17690)
-- Name: event_impact_summary; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.event_impact_summary AS
 SELECT event_id,
    event_name,
    event_start_date,
    event_start_time,
    category,
    venue_name,
    venue_id,
    event_measurements,
    baseline_measurements,
    event_avg_delay,
    baseline_avg_delay,
    impact_above_baseline,
        CASE
            WHEN (impact_above_baseline IS NULL) THEN 'unknown'::text
            WHEN (impact_above_baseline > (5)::numeric) THEN 'severe'::text
            WHEN (impact_above_baseline > (2)::numeric) THEN 'high'::text
            WHEN (impact_above_baseline > (1)::numeric) THEN 'moderate'::text
            ELSE 'low'::text
        END AS impact_level
   FROM public.event_traffic_with_baseline
  WHERE (event_measurements > 0);


ALTER VIEW public.event_impact_summary OWNER TO postgres;

--
-- TOC entry 5058 (class 0 OID 0)
-- Dependencies: 238
-- Name: VIEW event_impact_summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.event_impact_summary IS 'Simplified event impact view with classification levels';


--
-- TOC entry 236 (class 1259 OID 17671)
-- Name: event_traffic_data; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.event_traffic_data AS
 SELECT e.event_id,
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
    (EXTRACT(epoch FROM (tm.measurement_time - (e.event_start_date + e.event_start_time))) / (3600)::numeric) AS hours_from_event
   FROM ((public.events e
     JOIN public.venue_locations v ON ((e.venue_id = v.venue_id)))
     LEFT JOIN public.traffic_measurements tm ON ((v.venue_id = tm.venue_id)))
  WHERE ((e.event_start_time IS NOT NULL) AND ((tm.measurement_time >= ((e.event_start_date + e.event_start_time) - '02:00:00'::interval)) AND (tm.measurement_time <= ((e.event_start_date + e.event_start_time) + '02:00:00'::interval))));


ALTER VIEW public.event_traffic_data OWNER TO postgres;

--
-- TOC entry 5059 (class 0 OID 0)
-- Dependencies: 236
-- Name: VIEW event_traffic_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.event_traffic_data IS 'Events joined with traffic measurements within 2-hour window';


--
-- TOC entry 217 (class 1259 OID 16951)
-- Name: events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.events_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.events_event_id_seq OWNER TO postgres;

--
-- TOC entry 5060 (class 0 OID 0)
-- Dependencies: 217
-- Name: events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.events_event_id_seq OWNED BY public.events.event_id;


--
-- TOC entry 231 (class 1259 OID 17393)
-- Name: events_missing_traffic; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.events_missing_traffic AS
 SELECT e.event_id,
    e.event_name,
    e.event_start_date,
    e.event_start_time,
    e.category,
    v.venue_name,
    (e.event_start_date - CURRENT_DATE) AS days_until_event,
        CASE
            WHEN (e.event_start_date < CURRENT_DATE) THEN 'past'::text
            WHEN (e.event_start_date = CURRENT_DATE) THEN 'today'::text
            ELSE 'future'::text
        END AS event_status,
    ( SELECT count(*) AS count
           FROM public.traffic_measurements
          WHERE (traffic_measurements.event_id = e.event_id)) AS traffic_measurements,
        CASE
            WHEN (e.event_start_date > (CURRENT_DATE + 7)) THEN 'Too far in future'::text
            WHEN (e.event_start_date < (CURRENT_DATE - 7)) THEN 'Event already passed'::text
            WHEN (((e.event_start_date - CURRENT_DATE) <= 0) AND ((e.event_start_date - CURRENT_DATE) >= '-2'::integer)) THEN 'Should have data - check collector'::text
            ELSE 'Collection pending'::text
        END AS missing_reason
   FROM (public.events e
     JOIN public.venue_locations v ON ((e.venue_id = v.venue_id)))
  WHERE ((e.event_start_time IS NOT NULL) AND (NOT (EXISTS ( SELECT 1
           FROM public.traffic_measurements tm
          WHERE (tm.event_id = e.event_id)))))
  ORDER BY e.event_start_date, e.event_start_time;


ALTER VIEW public.events_missing_traffic OWNER TO postgres;

--
-- TOC entry 5061 (class 0 OID 0)
-- Dependencies: 231
-- Name: VIEW events_missing_traffic; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.events_missing_traffic IS 'Events that should have traffic data but don''t';


--
-- TOC entry 226 (class 1259 OID 17045)
-- Name: events_multi_day; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.events_multi_day AS
 SELECT event_id,
    event_name,
    venue_name,
    event_start_date,
    event_end_date,
    event_start_time,
    event_end_time,
    category,
    venue_id,
    ((event_end_date - event_start_date) + 1) AS duration_days
   FROM public.events
  WHERE ((is_multi_day = true) AND (event_start_date <> event_end_date));


ALTER VIEW public.events_multi_day OWNER TO postgres;

--
-- TOC entry 5063 (class 0 OID 0)
-- Dependencies: 226
-- Name: VIEW events_multi_day; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.events_multi_day IS 'Events spanning multiple days';


--
-- TOC entry 225 (class 1259 OID 17041)
-- Name: events_single_day; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.events_single_day AS
 SELECT event_id,
    event_name,
    venue_name,
    event_start_date AS event_date,
    event_start_time AS event_time,
    category,
    venue_id,
    created_at,
    updated_at
   FROM public.events
  WHERE ((is_multi_day = false) OR (event_start_date = event_end_date));


ALTER VIEW public.events_single_day OWNER TO postgres;

--
-- TOC entry 5065 (class 0 OID 0)
-- Dependencies: 225
-- Name: VIEW events_single_day; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.events_single_day IS 'Events occurring on a single day';


--
-- TOC entry 230 (class 1259 OID 17388)
-- Name: recent_collection_activity; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.recent_collection_activity AS
 SELECT date_trunc('hour'::text, measurement_time) AS collection_hour,
    count(*) AS measurements,
    count(
        CASE
            WHEN (is_baseline = true) THEN 1
            ELSE NULL::integer
        END) AS baseline_count,
    count(
        CASE
            WHEN (event_id IS NOT NULL) THEN 1
            ELSE NULL::integer
        END) AS event_count,
    count(DISTINCT venue_id) AS venues_measured,
    count(DISTINCT event_id) AS events_measured,
    data_source,
    avg(delay_minutes) AS avg_delay,
    min(measurement_time) AS first_measurement,
    max(measurement_time) AS last_measurement
   FROM public.traffic_measurements
  WHERE (measurement_time > (now() - '24:00:00'::interval))
  GROUP BY (date_trunc('hour'::text, measurement_time)), data_source
  ORDER BY (date_trunc('hour'::text, measurement_time)) DESC, data_source;


ALTER VIEW public.recent_collection_activity OWNER TO postgres;

--
-- TOC entry 5067 (class 0 OID 0)
-- Dependencies: 230
-- Name: VIEW recent_collection_activity; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.recent_collection_activity IS 'Hourly breakdown of collection activity in last 24 hours';


--
-- TOC entry 221 (class 1259 OID 16986)
-- Name: traffic_measurements_measurement_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.traffic_measurements_measurement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.traffic_measurements_measurement_id_seq OWNER TO postgres;

--
-- TOC entry 5069 (class 0 OID 0)
-- Dependencies: 221
-- Name: traffic_measurements_measurement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.traffic_measurements_measurement_id_seq OWNED BY public.traffic_measurements.measurement_id;


--
-- TOC entry 223 (class 1259 OID 17016)
-- Name: traffic_summary_by_venue; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.traffic_summary_by_venue AS
 SELECT v.venue_id,
    v.venue_name,
    count(tm.measurement_id) AS measurement_count,
    avg(tm.delay_minutes) AS avg_delay_minutes,
    max(tm.delay_minutes) AS max_delay_minutes,
    min(tm.measurement_time) AS first_measurement,
    max(tm.measurement_time) AS last_measurement
   FROM (public.venue_locations v
     LEFT JOIN public.traffic_measurements tm ON ((v.venue_id = tm.venue_id)))
  GROUP BY v.venue_id, v.venue_name;


ALTER VIEW public.traffic_summary_by_venue OWNER TO postgres;

--
-- TOC entry 5070 (class 0 OID 0)
-- Dependencies: 223
-- Name: VIEW traffic_summary_by_venue; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.traffic_summary_by_venue IS 'Summary statistics of traffic by venue';


--
-- TOC entry 228 (class 1259 OID 17211)
-- Name: venue_baseline_patterns; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.venue_baseline_patterns AS
 SELECT v.venue_id,
    v.venue_name,
    tm.day_of_week,
        CASE tm.day_of_week
            WHEN 0 THEN 'Sunday'::text
            WHEN 1 THEN 'Monday'::text
            WHEN 2 THEN 'Tuesday'::text
            WHEN 3 THEN 'Wednesday'::text
            WHEN 4 THEN 'Thursday'::text
            WHEN 5 THEN 'Friday'::text
            WHEN 6 THEN 'Saturday'::text
            ELSE NULL::text
        END AS day_name,
    tm.hour_of_day,
    count(*) AS measurement_count,
    avg(tm.delay_minutes) AS avg_delay,
    avg(tm.avg_speed_mph) AS avg_speed,
        CASE
            WHEN (avg(tm.delay_minutes) < (1)::numeric) THEN 'light'::text
            WHEN (avg(tm.delay_minutes) < (2)::numeric) THEN 'moderate'::text
            WHEN (avg(tm.delay_minutes) < (5)::numeric) THEN 'heavy'::text
            ELSE 'severe'::text
        END AS typical_traffic_level
   FROM (public.venue_locations v
     JOIN public.traffic_measurements tm ON ((v.venue_id = tm.venue_id)))
  WHERE ((tm.is_baseline = true) AND ((tm.baseline_type)::text = 'weekly'::text))
  GROUP BY v.venue_id, v.venue_name, tm.day_of_week, tm.hour_of_day
  ORDER BY v.venue_name, tm.day_of_week, tm.hour_of_day;


ALTER VIEW public.venue_baseline_patterns OWNER TO postgres;

--
-- TOC entry 5072 (class 0 OID 0)
-- Dependencies: 228
-- Name: VIEW venue_baseline_patterns; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.venue_baseline_patterns IS 'Baseline traffic patterns by venue, day of week, and hour';


--
-- TOC entry 219 (class 1259 OID 16970)
-- Name: venue_locations_venue_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.venue_locations_venue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.venue_locations_venue_id_seq OWNER TO postgres;

--
-- TOC entry 5074 (class 0 OID 0)
-- Dependencies: 219
-- Name: venue_locations_venue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.venue_locations_venue_id_seq OWNED BY public.venue_locations.venue_id;


--
-- TOC entry 232 (class 1259 OID 17398)
-- Name: venues_missing_baseline; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.venues_missing_baseline AS
 SELECT v.venue_id,
    v.venue_name,
    count(tm.measurement_id) AS total_baseline_measurements,
    count(DISTINCT tm.day_of_week) AS days_covered,
    count(DISTINCT tm.hour_of_day) AS hours_covered,
    max(tm.measurement_time) AS last_baseline_collection,
    EXTRACT(day FROM (now() - (max(tm.measurement_time))::timestamp with time zone)) AS days_since_baseline,
        CASE
            WHEN (count(tm.measurement_id) = 0) THEN 'No baseline data'::text
            WHEN (count(DISTINCT tm.day_of_week) < 7) THEN 'Incomplete day coverage'::text
            WHEN (count(DISTINCT tm.hour_of_day) < 6) THEN 'Incomplete hour coverage'::text
            WHEN (EXTRACT(day FROM (now() - (max(tm.measurement_time))::timestamp with time zone)) > (30)::numeric) THEN 'Baseline data outdated'::text
            ELSE 'Good coverage'::text
        END AS baseline_status
   FROM (public.venue_locations v
     LEFT JOIN public.traffic_measurements tm ON (((v.venue_id = tm.venue_id) AND (tm.is_baseline = true))))
  GROUP BY v.venue_id, v.venue_name
  ORDER BY (count(tm.measurement_id)), v.venue_name;


ALTER VIEW public.venues_missing_baseline OWNER TO postgres;

--
-- TOC entry 5075 (class 0 OID 0)
-- Dependencies: 232
-- Name: VIEW venues_missing_baseline; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.venues_missing_baseline IS 'Venues with incomplete or outdated baseline data';


--
-- TOC entry 4803 (class 2604 OID 16955)
-- Name: events event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events ALTER COLUMN event_id SET DEFAULT nextval('public.events_event_id_seq'::regclass);


--
-- TOC entry 4812 (class 2604 OID 16990)
-- Name: traffic_measurements measurement_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.traffic_measurements ALTER COLUMN measurement_id SET DEFAULT nextval('public.traffic_measurements_measurement_id_seq'::regclass);


--
-- TOC entry 4807 (class 2604 OID 16974)
-- Name: venue_locations venue_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.venue_locations ALTER COLUMN venue_id SET DEFAULT nextval('public.venue_locations_venue_id_seq'::regclass);


--
-- TOC entry 4815 (class 2606 OID 16961)
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (event_id);


--
-- TOC entry 4836 (class 2606 OID 16995)
-- Name: traffic_measurements traffic_measurements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.traffic_measurements
    ADD CONSTRAINT traffic_measurements_pkey PRIMARY KEY (measurement_id);


--
-- TOC entry 4823 (class 2606 OID 17040)
-- Name: events unique_event_enhanced; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT unique_event_enhanced UNIQUE (event_name, event_start_date, venue_name);


--
-- TOC entry 4826 (class 2606 OID 16982)
-- Name: venue_locations venue_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.venue_locations
    ADD CONSTRAINT venue_locations_pkey PRIMARY KEY (venue_id);


--
-- TOC entry 4828 (class 2606 OID 16984)
-- Name: venue_locations venue_locations_venue_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.venue_locations
    ADD CONSTRAINT venue_locations_venue_name_key UNIQUE (venue_name);


--
-- TOC entry 4816 (class 1259 OID 16963)
-- Name: idx_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_category ON public.events USING btree (category);


--
-- TOC entry 4817 (class 1259 OID 17038)
-- Name: idx_event_date_range; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_date_range ON public.events USING btree (event_start_date, event_end_date);


--
-- TOC entry 4818 (class 1259 OID 17037)
-- Name: idx_event_end_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_end_date ON public.events USING btree (event_end_date);


--
-- TOC entry 4819 (class 1259 OID 17036)
-- Name: idx_event_start_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_start_date ON public.events USING btree (event_start_date);


--
-- TOC entry 4820 (class 1259 OID 17010)
-- Name: idx_events_venue; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_events_venue ON public.events USING btree (venue_id);


--
-- TOC entry 4829 (class 1259 OID 17187)
-- Name: idx_traffic_baseline_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_traffic_baseline_type ON public.traffic_measurements USING btree (baseline_type, day_of_week, hour_of_day);


--
-- TOC entry 4830 (class 1259 OID 17183)
-- Name: idx_traffic_event; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_traffic_event ON public.traffic_measurements USING btree (event_id);


--
-- TOC entry 4831 (class 1259 OID 17004)
-- Name: idx_traffic_level; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_traffic_level ON public.traffic_measurements USING btree (traffic_level);


--
-- TOC entry 4832 (class 1259 OID 17002)
-- Name: idx_traffic_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_traffic_time ON public.traffic_measurements USING btree (measurement_time);


--
-- TOC entry 4833 (class 1259 OID 17001)
-- Name: idx_traffic_venue; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_traffic_venue ON public.traffic_measurements USING btree (venue_id);


--
-- TOC entry 4834 (class 1259 OID 17003)
-- Name: idx_traffic_venue_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_traffic_venue_time ON public.traffic_measurements USING btree (venue_id, measurement_time DESC);


--
-- TOC entry 4824 (class 1259 OID 16985)
-- Name: idx_venue_coords; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_venue_coords ON public.venue_locations USING btree (latitude, longitude);


--
-- TOC entry 4821 (class 1259 OID 16964)
-- Name: idx_venue_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_venue_name ON public.events USING btree (venue_name);


--
-- TOC entry 4837 (class 2606 OID 17005)
-- Name: events events_venue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES public.venue_locations(venue_id);


--
-- TOC entry 4838 (class 2606 OID 17178)
-- Name: traffic_measurements traffic_measurements_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.traffic_measurements
    ADD CONSTRAINT traffic_measurements_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(event_id);


--
-- TOC entry 4839 (class 2606 OID 16996)
-- Name: traffic_measurements traffic_measurements_venue_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.traffic_measurements
    ADD CONSTRAINT traffic_measurements_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES public.venue_locations(venue_id) ON DELETE CASCADE;


--
-- TOC entry 5013 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE traffic_measurements; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.traffic_measurements TO PUBLIC;


--
-- TOC entry 5015 (class 0 OID 0)
-- Dependencies: 235
-- Name: TABLE api_usage_by_day; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.api_usage_by_day TO PUBLIC;


--
-- TOC entry 5041 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE events; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.events TO PUBLIC;


--
-- TOC entry 5048 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE venue_locations; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.venue_locations TO PUBLIC;


--
-- TOC entry 5052 (class 0 OID 0)
-- Dependencies: 234
-- Name: TABLE collection_schedule_validation; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.collection_schedule_validation TO PUBLIC;


--
-- TOC entry 5054 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE collection_status_summary; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.collection_status_summary TO PUBLIC;


--
-- TOC entry 5056 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE data_quality_check; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.data_quality_check TO PUBLIC;


--
-- TOC entry 5062 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE events_missing_traffic; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.events_missing_traffic TO PUBLIC;


--
-- TOC entry 5064 (class 0 OID 0)
-- Dependencies: 226
-- Name: TABLE events_multi_day; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.events_multi_day TO PUBLIC;


--
-- TOC entry 5066 (class 0 OID 0)
-- Dependencies: 225
-- Name: TABLE events_single_day; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.events_single_day TO PUBLIC;


--
-- TOC entry 5068 (class 0 OID 0)
-- Dependencies: 230
-- Name: TABLE recent_collection_activity; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.recent_collection_activity TO PUBLIC;


--
-- TOC entry 5071 (class 0 OID 0)
-- Dependencies: 223
-- Name: TABLE traffic_summary_by_venue; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.traffic_summary_by_venue TO PUBLIC;


--
-- TOC entry 5073 (class 0 OID 0)
-- Dependencies: 228
-- Name: TABLE venue_baseline_patterns; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.venue_baseline_patterns TO PUBLIC;


--
-- TOC entry 5076 (class 0 OID 0)
-- Dependencies: 232
-- Name: TABLE venues_missing_baseline; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.venues_missing_baseline TO PUBLIC;


-- Completed on 2026-02-15 15:35:17

--
-- PostgreSQL database dump complete
--

\unrestrict tmsC25Sl3G1fzAOMWIPy0qsU6y0gk3AjYh2DJN16xh7Zo5vWvICVC9LCqpgKBPf

