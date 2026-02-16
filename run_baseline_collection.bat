@echo off
REM Baseline Traffic Collection - Automated Run
cd /d C:\Users\lanee\Desktop\whatspoppingABQ
call C:\Users\lanee\Desktop\whatspoppingABQ\venv\Scripts\activate.bat

echo ============================================ >> baseline_collection.log
echo Run started: %date% %time% >> baseline_collection.log
echo ============================================ >> baseline_collection.log

python C:\Users\lanee\Desktop\whatspoppingABQ\collectors\baseline_scheduler.py >> baseline_collection.log 2>&1

echo Run completed: %date% %time% >> baseline_collection.log
echo. >> baseline_collection.log