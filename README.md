# What's Popping ABQ - Event Impact Analytics Platform

> End-to-end data platform analyzing how events impact local traffic patterns in Albuquerque, NM. Features automated event scraping, real-time traffic monitoring, cloud database, and interactive dashboards.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud-green.svg)](https://supabase.com/)
[![Prefect](https://img.shields.io/badge/Prefect-3.0-orange.svg)](https://www.prefect.io/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[Live Dashboard](https://whatspoppingabq.streamlit.app/)** | **[GitHub](https://github.com/LoamySand/whatspoppingABQ)**

---

##  Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Live Demo](#live-demo)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Data Pipeline](#data-pipeline)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Usage & Cost Optimization](#api-usage--cost-optimization)
- [Results & Analytics](#results--analytics)
- [Lessons Learned](#lessons-learned)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [Author](#author)

---

##  Overview

**What's Popping ABQ** is a production-ready data platform that automatically:

1. **Scrapes** upcoming events from Visit Albuquerque
2. **Geocodes** unique venues across Albuquerque
3. **Collects** real-time traffic data using TomTom API
4. **Analyzes** event impact using speed-based traffic metrics
5. **Visualizes** results in an interactive Streamlit dashboard
6. **Deploys** to cloud (Supabase + Streamlit Cloud)

**Business Value:** Helps city planners, event organizers, and local businesses understand how events affect traffic patterns and plan accordingly.

---

##  Key Features

### Data Engineering
-  **Automated Web Scraping** - Selenium handles JavaScript-rendered event calendars
-  **Smart Data Collection** - Event-triggered traffic monitoring with 4-week baseline rotation
-  **API Cost Optimization** - 75% reduction through single-point measurement strategy
-  **Cloud Database** - Supabase PostgreSQL with automatic backups
-  **Zero Downtime** - Prefect orchestration with automatic retries and error handling

### Data Quality
-  **Deduplication** - Upsert logic prevents duplicate events
-  **Geocoding** - All venues mapped with latitude/longitude
-  **Data Validation** - Multi-tier baseline fallback for 80%+ data coverage
-  **Quality Tracking** - Metadata on collection timing and match quality

### Analytics & Visualization
-  **Speed-Based Impact** - Custom delay calculation that is more reliable than provider-reported delay metrics
-  **Interactive Dashboard** - Live Streamlit app deployed to cloud
-  **Historical Comparison** - Baseline traffic patterns vs. event conditions
-  **Category Analysis** - Impact breakdown by event type (sports, music, festivals)

---

##  Live Demo

**[View Dashboard →](https://whatspoppingabq.streamlit.app/)**

The dashboard shows:
- Events analyzed with traffic impact measurements
- Impact above baseline (speed-based calculation)
- Geographic distribution of events and impact
- Category-level traffic statistics
- Data quality indicators

**Note:** Dashboard updates as new traffic data is collected (every 30 minutes for events, 6x/day for baseline).

---

##  Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.11 | Core development |
| **Web Scraping** | Selenium + BeautifulSoup | Event data extraction |
| **Database** | PostgreSQL 16 (Supabase) | Cloud data warehouse |
| **Orchestration** | Prefect 3.0 | Workflow automation |
| **Dashboard** | Streamlit | Interactive visualization |
| **Traffic API** | TomTom Traffic Flow API | Real-time traffic data |
| **Geocoding** | Google Maps Geocoding API | Venue coordinates |
| **Deployment** | Streamlit Cloud + Supabase | Production hosting |
| **Data Processing** | Pandas, NumPy | Data manipulation |
| **Version Control** | Git + GitHub | Source control |

---

##  Architecture

### System Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                               │
├─────────────────────────────────────────────────────────────────┤
│  Visit Albuquerque    TomTom Traffic API    Google Maps API     │
│  (Event Calendar)     (Speed/Delay Data)    (Geocoding)         │
└──────────┬───────────────────┬─────────────────────┬────────────┘
           │                   │                     │
           ▼                   ▼                     ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │  Event       │    │  Traffic     │    │  Venue       │
    │  Scraper     │    │  Collector   │    │  Geocoder    │
    │  (Selenium)  │    │  (TomTom)    │    │  (G Maps)    │
    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
           │                   │                   │
           └───────────────────┼───────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Prefect Flows      │
                    │  ┌────────────────┐  │
                    │  │ Event Scraping │  │  Weekly (Mondays 9am)
                    │  ├────────────────┤  │
                    │  │ Event Traffic  │  │  Every 30 minutes
                    │  ├────────────────┤  │
                    │  │ Baseline       │  │  6x/day (4-week rotation)
                    │  └────────────────┘  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Supabase PostgreSQL │
                    │  ┌────────────────┐  │
                    │  │ events         │  │
                    │  ├────────────────┤  │
                    │  │ venues         │  │
                    │  ├────────────────┤  │
                    │  │ traffic_data   │  │
                    │  ├────────────────┤  │
                    │  │ views          │  │
                    │  └────────────────┘  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Streamlit Dashboard │
                    │  (Cloud Hosted)      │
                    │                      │
                    │  - Event impact map  │
                    │  - Category analysis │
                    │  - Timeline charts   │
                    │  - Data quality viz  │
                    └──────────────────────┘
```

### Database Schema
```sql
-- Core tables
events               -- Events with dates, venues, categories
venue_locations      -- Eeocoded venues with coordinates
traffic_measurements -- Speed/delay measurements

-- Analytics views
event_traffic_with_baseline  -- Event vs baseline comparison
event_impact_summary         -- Impact metrics by event
category_traffic_impact      -- Category-level statistics
venue_baseline_patterns      -- Historical traffic patterns
event_impact_detail          -- Comprehensive event analysis
```

---

##  Data Pipeline

### Event Ingestion (Weekly)
```
1. Selenium → Navigate to Visit Albuquerque
2. Scrape → Extract event details (name, venue, date, category)
3. Validate → Check required fields, parse dates
4. Geocode → Match venues to coordinates (one-time)
5. Load → Upsert to PostgreSQL (prevent duplicates)
6. Report → Log summary statistics
```

**Runs:** Weekly on Mondays at 9am  
**Duration:** ~5 minutes  

### Traffic Collection (Automated)

#### Event Traffic
```
1. Query → Find events within ±2 hours
2. Collect → 9 measurements per event (every 30 min)
3. Store → Link to event_id with metadata
```

**Runs:** Every 30 minutes  
**Duration:** ~5 seconds  

#### Baseline Traffic
```
1. Schedule → 4-week rotation (2 groups of ~40 venues each)
2. Collect → 6 times/day (7am, 12pm, 5pm, 7pm, 9pm, 11pm)
3. Store → Mark as baseline with day_of_week, hour_of_day
```

**Runs:** Active 2 weeks/month  
**Duration:** ~1 minute  

### Traffic Impact Analysis
```
1. Match → Event traffic to baseline (same day/hour preferred)
2. Calculate → Impact = (Distance/EventSpeed - Distance/BaselineSpeed) × 60
3. Classify → Severe (>5 min) | High (>2 min) | Moderate (>1 min) | Low
4. Track → Data quality (exact match > same hour > same day > venue avg)
```

---

##  Getting Started

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 16+**
- **Git**
- **API Keys:** TomTom (free tier), Google Maps (optional for geocoding)

### Installation

**1. Clone repository**
```powershell
git clone https://github.com/LoamySand/whatspoppingABQ.git
cd whatspoppingABQ
```

**2. Set up Python environment**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**3. Configure environment**

Create `.env`:
```bash
# Database (Supabase)
DB_HOST=aws-1-us-east-2.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.YOUR_PROJECT_ID
DB_PASSWORD=your-supabase-password

# APIs
TOMTOM_API_KEY=your-tomtom-key
GOOGLE_MAPS_API_KEY=your-google-key  # Optional
```

**4. Initialize database**
```powershell
# Connect to Supabase (or local PostgreSQL)
psql "postgresql://postgres:PASSWORD@PROJECT.supabase.co:5432/postgres"

# Run migrations
\i database/schema/event_analytics_schema.sql
```

**5. Test the pipeline**
```powershell
# Test event scraping
python flows\ingest_events.py

# Test traffic collection
python collectors\tomtom_event_traffic_collector.py

# Run dashboard locally
streamlit run dashboard\event_traffic_dashboard.py
```

---

##  Usage

### Manual Execution

**Run event scraping:**
```powershell
python -m flows.ingest_events_enhanced
```

**Collect event traffic:**
```powershell
python collectors\tomtom_event_traffic_collector.py
```

**Collect baseline traffic:**
```powershell
python collectors\baseline_schedule.py
```

**View dashboard:**
```powershell
streamlit run dashboard\event_traffic_dashboard.py
```

### Automated Execution (Prefect)

**Start Prefect services:**
```powershell
# Terminal 1: Start Prefect server
prefect server start

# Terminal 2: Start all flows
python run_prefect_flows.py
```

**Monitor at:** http://localhost:4200

**Deployed flows:**
- `event-traffic` - Every 30 minutes
- `baseline-7am` through `baseline-11pm` - 6x daily
- `event-scraping-weekly` - Mondays at 9am

### Database Queries

**Event impact analysis:**
```sql
-- Top 10 highest impact events
SELECT 
    event_name,
    venue_name,
    impact_above_baseline,
    impact_level
FROM event_impact_summary
ORDER BY impact_above_baseline DESC
LIMIT 10;

-- Category statistics
SELECT 
    category,
    avg_impact_minutes,
    pct_high_impact
FROM category_traffic_impact
ORDER BY avg_impact_minutes DESC;
```

---

##  Project Structure
```
whatspoppingABQ/
├── collectors/                      # Traffic data collection
│   ├── tomtom_flow_collector.py    # TomTom API wrapper
│   ├── tomtom_event_traffic_collector.py   # Event-triggered collection
│   └── baseline_scheduler.py       # 4-week rotation scheduler
│
├── database/                        # Database layer
│   ├── schema/                      # Initial table definitions
│   └── db_utils.py                 # Connection & query utilities
│
├── dashboard/                       # Visualization
│   └── event_traffic_dashboard.py  # Streamlit app
│
├── flows/                           # Prefect workflows
│   ├── ingest_events.py            # Event scraping flow
│   ├── ingest_events_enhanced.py   # Enhanced scraper
│   └── collect_traffic.py          # Traffic collection flows
│
├── scrapers/                        # Web scraping
│   ├── visit_abq_detail_scraper.py        # Selenium scraper
│
├── scripts/                         # Utility scripts
│   ├── geocode_venues.py           # Bulk geocoding
│   ├── backfill_metadata.py        # Data quality fixes
│   ├── validate_collection.py      # Data validation
│   └── check_collection_schedule.py # API usage reporting
│
├── utils/                           # Helper functions
│   └── geocoding.py                # Google Maps geocoding
│
├── run_prefect_flows.py            # Unified Prefect server
├── startup_all.bat                 # Windows automation
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
└── README.md                       # This file
```

---

##  API Usage & Cost Optimization

### Strategy Evolution

**Initial Approach (High Cost):**
- Google Maps Routing API for both baseline and events
- 4 directional measurements per point
- **Projected cost:** $32.87/month

**Optimized Approach (Zero Cost):**
- TomTom Traffic Flow API (free 2,500 calls/day)
- Single-point measurement at venue
- 4-week baseline rotation
- **Actual cost:** $0/month

### Current API Usage

| Service | Calls/Day | Monthly | Cost |
|---------|-----------|---------|------|
| **Baseline** | 120 (peak weeks) | 3,360 | $0 |
| **Event Traffic** | 27 (avg) | 810 | $0 |
| **Total** | 147 | 4,170 | **$0** |

**Free Tier:** 2,500 calls/day (TomTom)  
**Peak Usage:** 160 calls/day (6% of limit)  
**Savings:** 75% reduction through single-point strategy

### Optimization Techniques

1. **Single-Point Measurement** - Measure at venue instead of 4 directions
2. **4-Week Rotation** - Venues dynamically split into collection groups to minimize daily calls
3. **Smart Scheduling** - Events collected only within ±2 hours window

---

### Key Insights

**Traffic Impact by Category:**
- Sports events: Highest average impact
- Music/festivals: Variable impact (venue-dependent)
- Community events: Generally lower impact

**Speed-Based vs Delay-Based:**
- Speed differences detect impact in 95% of events
- TomTom-reported delay shows 0 in 60% of cases
- **Lesson:** Calculate impact from speed, don't rely on API delay values

---

### Data Engineering Principles Applied

 **Incremental Development** - Built and validated each component separately  
 **Cost Optimization** - Reduced API costs by 75% through smart design  
 **Data Quality** - Multi-tier fallback ensures 80%+ baseline coverage  
 **Automation** - Zero manual intervention after deployment  
 **Error Handling** - Retry logic and fallbacks prevent pipeline failures  
 **Documentation** - Comprehensive migration tracking and API usage docs  

---

##  Future Enhancements

### Phase 1: Self-Hosted Infrastructure
- [ ] Set up Raspberry Pi/NUC server
- [ ] Docker Compose stack (PostgreSQL + Prefect + Dashboard)
- [ ] Migrate from Supabase to self-hosted PostgreSQL

### Phase 2: Advanced Analytics
- [ ] Machine learning impact prediction
- [ ] Historical trend analysis
- [ ] Event attendance estimation
- [ ] Traffic pattern clustering

### Phase 3: Multi-Source Integration
- [ ] Yelp business review sentiment
- [ ] Reddit community discussion analysis
- [ ] Weather correlation analysis

### Phase 4: Business Intelligence
- [ ] Automated weekly reports
- [ ] Email/Slack notifications for high-impact events
- [ ] Mobile app for real-time updates
- [ ] Public API for data access

---

##  Contributing

This is a portfolio project, but feedback is welcome!

**To suggest improvements:**
1. Open an issue describing the enhancement
2. Fork the repository
3. Create a feature branch
4. Submit a pull request

---

##  License

MIT License - See [LICENSE](LICENSE) file

---

##  Author

**Lane Boyd**

Data Engineer | ETL Pipeline Specialist | Cloud Architecture

- **Portfolio:** [whatspoppingabq.streamlit.app](https://whatspoppingabq.streamlit.app)
- **GitHub:** [@LoamySand](https://github.com/LoamySand)
- **LinkedIn:** [lane-boyd](https://www.linkedin.com/in/lane-boyd-48862715a/)
- **Email:**  LaneEBoyd@gmail.com

**Skills Demonstrated:**
- End-to-end data pipeline development
- Web scraping (Selenium, BeautifulSoup)
- API integration and cost optimization
- PostgreSQL database design and optimization
- Workflow orchestration (Prefect)
- Cloud deployment (Supabase, Streamlit Cloud)
- Data visualization (Streamlit, Plotly)
- Production automation and monitoring

---

##  Acknowledgments

- **TomTom** for free-tier Traffic API access
- **Supabase** for cloud PostgreSQL hosting
- **Streamlit** for cloud dashboard deployment
- **Visit Albuquerque** for event data source

---

*Built with ❤️ (or 💚?) in Albuquerque, New Mexico (IYKYK)*

*Last Updated: February 2026*