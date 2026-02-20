# What's Popping ABQ - Event Impact Analytics Pipeline

> End-to-end data pipeline analyzing event impacts on local traffic, businesses, and community sentiment in Albuquerque, NM.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Prefect](https://img.shields.io/badge/Prefect-3.0-orange.svg)](https://www.prefect.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

##  Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Pipeline Details](#pipeline-details)
- [Results](#results)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

---

## Overview

This project demonstrates end-to-end data engineering skills by building an automated pipeline that:

1. **Scrapes** event data from Visit Albuquerque using Selenium
2. **Validates** data quality and consistency
3. **Loads** events into PostgreSQL with upsert logic
4. **Orchestrates** workflows with Prefect
5. **Schedules** daily execution via Windows Task Scheduler

**Use Case:** Analyze how major events (sports, festivals, concerts) impact local businesses, traffic patterns, and community sentiment.

**[Demo](https://whatspoppingabq.streamlit.app/)**

---

##  Features

- **Automated Web Scraping** - Selenium handles JavaScript-rendered content
- **Data Quality Validation** - Ensures clean, consistent data
- **PostgreSQL Data Warehouse** - Scalable storage with proper indexing
- **Workflow Orchestration** - Prefect manages task dependencies
- **Error Handling** - Retry logic and failure handling
- **Scheduled Execution** - Runs daily without manual intervention
- **No Duplicates** - Upsert logic prevents duplicate records
- **Comprehensive Logging** - Full visibility into pipeline execution

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.11 | Core development |
| **Web Scraping** | Selenium + BeautifulSoup | Extract event data |
| **Database** | PostgreSQL 15 | Data warehouse |
| **Orchestration** | Prefect 3.0 | Workflow management |
| **Scheduling** | Windows Task Scheduler | Automated execution |
| **Data Processing** | Pandas | Data manipulation |
| **Version Control** | Git + GitHub | Source control |

---

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Visit Albuquerque                         │
│                  (Event Source Website)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  Selenium      │  → Handles JavaScript rendering
            │  Web Scraper   │  → Navigates pagination
            └────────┬───────┘  → Extracts structured data
                     │
                     ▼
            ┌────────────────┐
            │   Data         │  → Validates required fields
            │   Validation   │  → Checks date formats
            └────────┬───────┘  → Filters invalid events
                     │
                     ▼
            ┌────────────────┐
            │  PostgreSQL    │  → Stores events
            │  Database      │  → Prevents duplicates (upsert)
            └────────┬───────┘  → Indexes for performance
                     │
                     ▼
            ┌────────────────┐
            │   Prefect      │  → Orchestrates tasks
            │   Flow         │  → Handles retries
            └────────┬───────┘  → Generates reports
                     │
                     ▼
            ┌────────────────┐
            │   Windows      │  → Runs daily at 6 AM
            │   Task         │  → No manual intervention
            │   Scheduler    │  → Production automation
            └────────────────┘
```

---

##  Getting Started

### Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 15+** - [Download](https://www.postgresql.org/download/windows/)
- **Git** - [Download](https://git-scm.com/download/win)
- **Windows 10/11** (or WSL for Linux)

### Installation

**1. Clone the repository**
```powershell
git clone https://github.com/LoamySand/whatspoppingABQ.git
cd whatspoppingABQ
```

**2. Create virtual environment**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**3. Install dependencies**
```powershell
pip install -r requirements.txt
```

**4. Configure database**

Create `.env` file:
```bash
# Copy example file
copy .env.example .env
```

Edit `.env` and add your PostgreSQL password:
```
DB_PASSWORD=your_postgres_password
```

**5. Set up PostgreSQL**

Open SQL Shell (psql):
```sql
CREATE DATABASE event_analytics;
\c event_analytics
\i C:/Users/[YourPath]/whatspoppingABQ/database/schema.sql
\q
```

**6. Test the pipeline**
```powershell
python flows\ingest_events.py
```

---

## Usage

### Manual Execution

**Run the pipeline once:**
```powershell
.\venv\Scripts\Activate.ps1
python flows\ingest_events.py
```

**Quick demo (1 page):**
```powershell
python demo_pipeline.py
```

### Automated Execution

**Set up Windows Task Scheduler:**

1. Test batch file: `.\run_pipeline.bat`
2. Open Task Scheduler: `Win + R` → `taskschd.msc`
3. Create Basic Task:
   - Name: "Event Pipeline Daily"
   - Trigger: Daily at 6:00 AM
   - Action: Start `run_pipeline.bat`
   - Start in: Project directory

**The pipeline now runs automatically every day!**

### Database Queries

**Check pipeline results:**
```sql
-- Connect to database
\c event_analytics

-- Total events
SELECT COUNT(*) FROM events;

-- Events by category
SELECT category, COUNT(*) 
FROM events 
GROUP BY category 
ORDER BY COUNT(*) DESC;

-- Recent events
SELECT event_name, venue_name, event_date 
FROM events 
ORDER BY updated_at DESC 
LIMIT 10;
```

---

## Project Structure
```
whatspoppingABQ/
├── database/                                   # Database schemas and utilities
│   ├── schema.sql                              # PostgreSQL table definitions
│   ├── db_utils.py                             # Database connection & queries
│   └── README.md                               # Database documentation
│
├── scrapers/                                   # Web scraping modules
│   └── visit_abq_scraper.py                    # Selenium-based scraper
│
├── collectors/                                 # API calls
│   ├── traffic_collection_rules.py             # Configuration of API calls based on event data
|   ├── traffic_collector.py                    # Collect traffic_measurement data via API call to Google Maps
|
├── flows/                                      # Prefect workflow definitions
│   └── ingest_events.py                        # Main pipeline flow
│
├── scripts/                                    # helper scripts meant to be manually run
│   ├── ..
│
├── utils/                                      # Helper scripts used by scrapers, collectors, and flows
│   ├── ..
│
├── venv/                                       # Virtual environment (not tracked)
            
├── .env                                        # Environment variables (not tracked)
├── .env.example                                # Environment template
├── .gitignore                                  # Git ignore rules
├── README.md                                   # This file
├── requirements.txt                            # Python dependencies
├── run_pipeline.bat                            # Automated execution script
├── demo_pipeline.py                            # Demo script
└── test_end_to_end.py                          # E2E test suite
```

---

## Pipeline Details

### Data Flow

1. **Scraping** 
   - Selenium launches headless Chrome
   - Navigates to Visit Albuquerque events page
   - Clicks "Next" to paginate through results
   - Extracts: event name, venue, date, category

2. **Collecting**
   - Prefect Flow triggers DB query for upcoming 
2. **Validation**
   - Checks required fields (name, date)
   - Validates date formats (YYYY-MM-DD)
   - Filters out invalid/incomplete events

3. **Loading** 
   - Inserts events into PostgreSQL
   - Uses `ON CONFLICT` for upsert logic
   - No duplicates created
   - Indexes ensure fast queries

4. **Reporting**
   - Counts events by category
   - Logs summary statistics
   - Reports new vs. updated events

--- 

## Future Enhancements

### Sprint 2: Traffic Data Integration
- [x] Integrate Google Maps Traffic API
- [x] Correlate events with traffic patterns
- ~~[ ] Store historical traffic data~~ moved to backlog

### Sprint 3: Visualization Dashboard
- [X] Build interactive dashboard
- [ ] Visualize event impact metrics
- [ ] Generate automated reports

### Sprint 4: Business Sentiment
- [ ] Scrape Yelp reviews for venues
- [ ] Implement NLP sentiment analysis
- [ ] Track review volume changes

### Sprint 5: Social Media Analytics
- [ ] Add Reddit API for community sentiment
- [ ] Analyze event-related discussions
- [ ] Track social media engagement

### Sprint 6: Production Deployment
- [ ] Containerize with Docker
- [ ] Deploy to cloud (AWS/GCP)
- [ ] Set up monitoring and alerts
- [ ] Implement CI/CD pipeline

---

## Contributing

This is a personal portfolio project, but suggestions are welcome!

**To suggest improvements:**
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with description

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

**Lane Boyd**

- GitHub: [@LoamySand](https://github.com/LoamySand)
- Focus: ETL, Orchestration, Data Warehousing
- Connect on [LinkedIn](https://www.linkedin.com/in/lane-boyd-48862715a/)

---

*Last Updated: February 2026*