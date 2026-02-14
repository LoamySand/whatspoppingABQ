# Quick Start Guide

## Prerequisites Check

Before starting, verify you have:
- [ ] Python 3.11+ installed
- [ ] PostgreSQL 15+ installed and running
- [ ] Git installed
- [ ] 500 MB free disk space

---

## Step 1: Clone & Setup (5 minutes)
```powershell
# Clone repository
git clone https://github.com/LoamySand/whatspoppingABQ.git
cd whatspoppingABQ

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Database (5 minutes)

**Create database:**
```powershell
# Open SQL Shell (psql) from Start Menu
# Press Enter 4 times, enter password
```
```sql
CREATE DATABASE event_analytics;
\c event_analytics
\i C:/Users/[YourPath]/whatspoppingABQ/database/schema.sql
\q
```

**Set password:**
```powershell
copy .env.example .env
notepad .env
```

Edit: `DB_PASSWORD=your_actual_password`

---

## Step 3: Test Pipeline (5 minutes)
```powershell
# Activate venv (if not active)
.\venv\Scripts\Activate.ps1

# Run pipeline
python flows\ingest_events.py
```

**Wait ~70 seconds.** You should see:
```
✅ Pipeline completed successfully!
```

**Verify in database:**
```sql
\c event_analytics
SELECT COUNT(*) FROM events;
```

---

## Step 4: Schedule (Optional)

**For automated daily runs:**

1. Test batch file: `.\run_pipeline.bat`
2. Open Task Scheduler: `Win + R` → `taskschd.msc`
3. Create Basic Task → Daily 6 AM → Run `run_pipeline.bat`

---

## Troubleshooting

**"No module named 'prefect'"**
→ Activate venv: `.\venv\Scripts\Activate.ps1`

**Database connection failed**
→ Check `.env` password is correct

**No events scraped**
→ Check internet connection

**Permission denied**
→ Run as Administrator or check file permissions


---

**Need help?** Create an issue on GitHub.