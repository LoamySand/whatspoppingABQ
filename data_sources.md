# Event Data Sources for Albuquerque Pipeline

## Overview

This document tracks potential data sources for event information in Albuquerque, NM. We need sources that provide:
- Event name and date
- Venue/location
- Event category/type
- Ideally: time, attendance, description

## Primary Sources

### 1. Visit Albuquerque Events Calendar

**URL:** https://www.visitalbuquerque.org/events/

**Description:** Official tourism website for Albuquerque. Aggregates major events across the city.

**Data Format:**
- HTML event listings
- Paginated results
- 
```html  

<div class="date-banner">
    <div class="day">11</div>
    <div class="month">Feb</div>
</div>
<div class="content-container">
    <div class="title">2025-2026 UNM Lobos Women's Basketball Season</div>
    <div class="location">University Arena (“the Pit”)</div>
</div>
```

**Event Types:**
- Festivals
- Concerts
- Sports
- Cultural events
- Community events

**Update Frequency:** Daily

**Pros:**
-  Official source (reliable)
-  Broad coverage of events
-  Well-maintained
-  Multiple event types
-  Year-round events

**Cons:**
-  May not include all small events
-  HTML structure may change

**Scraping Complexity:** Medium

**Data Quality:** High

---

### 2. Albuquerque Isotopes Schedule

**URL:** https://www.milb.com/albuquerque/schedule/2025-02

**Description:** Official schedule for Albuquerque Isotopes (AAA baseball team).

**Data Format:**
- Structured schedule/calendar view
- 
```html 
<div class="time-or-score">
<a href="/gameday/780260/final/box" class="time">
    <div class="primary-time"></div>
    <div class="supp-time"></div>
</a>
<a class="score" href="/gameday/780260/final/box" role="button" aria-label="Albuquerque Isotopes 1 - Salt Lake 15 Top 9">
    <span class="inning-or-outcome">
        <span class="inning">B9: </span>
        <span class="outcome">L, </span>
    </span>
    <span class="left-score-tricode score-tricode"></span>
    <span class="left-score">1</span>
    <span class="hyphen">-</span>
    <span class="right-score-tricode score-tricode"></span>
    <span class="right-score">15</span>
</a>
<div class="special-game-state-notice"></div>
</div>
```

**Event Types:**
- Baseball games (home games ~70 per season)
- Special events at Isotopes Park

**Season:** April - September (regular season)

**Update Frequency:** Schedule set at season start, updated for changes

**Pros:**
-  Highly structured data
-  Predictable schedule
-  Known attendance patterns
-  Consistent venue (Isotopes Park, 1601 Avenida Cesar Chavez SE)
-  Easy to scrape

**Cons:**
-  Seasonal (limited to baseball season)
-  Single venue/event type
-  Currently off-season

**Scraping Complexity:** Low

**Data Quality:** Very High


---

### 3. Eventbrite Albuquerque

**URL:** https://www.eventbrite.com/d/nm--albuquerque/events/

**Description:** Community event platform with many local events.

**Data Format:**
- HTML/JavaScript rendered listings
- Dynamic loading (may require Selenium)
- [TODO: Add specific structure after inspection]

**Event Types:**
- Community events
- Workshops
- Concerts
- Classes
- Meetups
- Fundraisers

**Update Frequency:** Continuous (user-generated)

**Pros:**
-  High volume of events
-  Diverse event types
-  Year-round coverage
-  Includes smaller community events
-  Good for variety

**Cons:**
-  May require JavaScript rendering (Selenium)
-  Data quality varies (user-generated)
-  Some events may be cancelled/outdated
-  Potential duplicate listings

**Scraping Complexity:** Medium-High (may need Selenium)

**Data Quality:** Medium (user-generated, needs validation)


---

## Approach

### Phase 1 (Sprint 1): Single Source
**Start with:** Visit Albuquerque Events
- Easiest to implement
- Broadest coverage
- Good for MVP

### Phase 2 (Sprint 2): Add Sports Data
**Add:** Isotopes Schedule
- Structured data (easy integration)
- Demonstrates multi-source capability
- Different data format

### Phase 3 (Future): Community Events
**Add:** Eventbrite (if time permits)
- Shows ability to handle complex scraping
- Adds volume and variety

---

## Data Mapping

All sources should map to our events table:

| Our Field | Visit ABQ | Isotopes | Eventbrite |
|-----------|-----------|----------|------------|
| event_name | Event title | Game title | Event name |
| venue_name | Venue field | "Isotopes Park" | Venue |
| event_date | Date | Game date | Start date |
| event_time | Time | Game time | Start time |
| category | Event type | "Sports - Baseball" | Category |
| latitude | Venue coords | 35.0781 | Venue coords |
| longitude | Venue coords | -106.6044 | Venue coords |
| source_url | Event URL | Schedule URL | Event URL |

---
