@echo off
REM Event Pipeline - Automated Daily Run
cd C:\Users\lanee\Desktop\whatspoppingABQ
call venv\Scripts\activate.bat

echo ============================================================
echo Running Event Ingestion Pipeline
echo Started: %date% %time%
echo ============================================================
echo.

python flows\ingest_events.py

echo.
echo ============================================================
echo Pipeline Complete: %date% %time%
echo ============================================================