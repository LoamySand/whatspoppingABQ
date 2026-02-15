@echo off
REM Traffic Collection - Automated Hourly Run

REM Change to project directory
cd /d C:\Users\lanee\Desktop\whatspoppingABQ

REM Activate virtual environment (absolute path)
call C:\Users\lanee\Desktop\whatspoppingABQ\venv\Scripts\activate.bat

REM Run script
python C:\Users\lanee\Desktop\whatspoppingABQ\scripts\auto_collect_traffic_tomtom.py >> C:\Users\lanee\Desktop\whatspoppingABQ\traffic_collection.log 2>&1

REM Deactivate
call deactivate