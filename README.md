# What's Popping ABQ - Event Impact Analytics Pipeline

Data pipeline analyzing the impact of events on local traffic, businesses, and community sentiment in Albuquerque, NM.

## Overview

This project builds an automated data pipeline that:
- Scrapes event data from multiple sources
- Stores data in PostgreSQL
- Analyzes impact on local traffic and businesses
- Tracks community sentiment
- Orchestrates workflows with Prefect

## Tech Stack

- **Python 3.11** - Core language
- **Prefect** - Workflow orchestration
- **PostgreSQL 15** - Data warehouse
- **Selenium + BeautifulSoup4** - Web scraping (handles JavaScript-rendered sites)
- **Pandas** - Data processing
- **psycopg2** - PostgreSQL adapter

## Prerequisites

Before starting, ensure you have:
- **Python 3.11+** installed ([download](https://www.python.org/downloads/))
- **PostgreSQL 15+** installed ([download](https://www.postgresql.org/download/windows/))
- **Git** installed ([download](https://git-scm.com/download/win))
- Windows 10/11

## Quick Start

### 1. Clone Repository
```powershell
git clone https://github.com/LoamySand/whatspoppingABQ.git
cd whatspoppingABQ
```

### 2. Set Up Python Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL Database

Open **SQL Shell (psql)** from Start Menu:
- Press Enter 4 times to accept defaults
- Enter your PostgreSQL password
```sql
-- Create database
CREATE DATABASE event_analytics;

-- Connect to database
\c event_analytics

-- Create schema (after completing Issue #2)
\i database\schema.sql

-- Exit
\q
```

### 4. Configure Database Connection

Edit `database\db_utils.py` (when created in Issue #5):
```python
DB_CONFIG = {
    'dbname': 'event_analytics',
    'user': 'postgres',
    'password': 'YOUR_POSTGRES_PASSWORD',  # ⚠️ Change this!
    'host': 'localhost',
    'port': '5432'
}
```

### 5. Start Prefect Server

**Terminal 1:**
```powershell
cd whatspoppingABQ
.\venv\Scripts\Activate.ps1
prefect server start
```

Access Prefect UI at: **http://localhost:4200**

### 6. Run the Pipeline

**Terminal 2:**
```powershell
cd whatspoppingABQ
.\venv\Scripts\Activate.ps1
python flows\ingest_events.py
```

## Project Structure
```
whatspoppingABQ/
├── database/           # Database schema and connection utilities
│   ├── __init__.py
│   ├── schema.sql
│   └── db_utils.py
├── scrapers/           # Web scraping modules
│   ├── __init__.py
│   └── isotopes_scraper.py
├── flows/              # Prefect workflow definitions
│   ├── __init__.py
│   └── ingest_events.py
├── docs/               # Documentation and research
│   └── data_sources.md
├── venv/               # Virtual environment (not committed)
├── .gitignore
├── README.md
└── requirements.txt
```

## Development Workflow

**Every time you start working:**
```powershell
# 1. Navigate to project
cd C:\Users\lanee\Desktop\whatspoppingABQ

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Make changes, test, commit
git add .
git commit -m "description of changes"
git push origin main
```

## Sprint Progress

### Sprint 1: Basic Event Ingestion Pipeline

- [x] **Issue #1:** Development environment setup
- [x] **Issue #2:** Create database schema
- [x] **Issue #3:** Research data sources
- [x] **Issue #4:** Build event scraper
- [ ] **Issue #5:** Create database utilities
- [ ] **Issue #6:** Build Prefect flow
- [ ] **Issue #7:** End-to-end testing
- [ ] **Issue #8:** Documentation

### Future Sprints

- Sprint 2: Traffic data integration
- Sprint 3: Business review scraping
- Sprint 4: Sentiment analysis
- Sprint 5: Data quality & monitoring
- Sprint 6: Visualization dashboard

## Contributing

This is a personal portfolio project, but suggestions are welcome via Issues.

## Author

**Lane Boyd**
- GitHub: [@LoamySand](https://github.com/LoamySand)
- Project: Data Engineering Portfolio

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built as part of a data engineering portfolio project
- Focused on demonstrating ETL, orchestration, and analytics skills