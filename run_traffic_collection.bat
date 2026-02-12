@echo off
REM Traffic Collection - Automated Hourly Run
cd C:\Users\lanee\Desktop\whatspoppingABQ
call venv\Scripts\activate.bat

python scripts\auto_collect_traffic.py >> traffic_collection.log 2>&1