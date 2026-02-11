# start_dev.ps1 - Quick development environment setup

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "What's Popping ABQ - Dev Setup" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "Environment ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Python Version:" -ForegroundColor Cyan
python --version
Write-Host ""
Write-Host "Prefect Version:" -ForegroundColor Cyan
prefect version
Write-Host ""
Write-Host "Quick Commands:" -ForegroundColor Cyan
Write-Host "  prefect server start       - Start Prefect UI"
Write-Host "  python flows\ingest_events.py - Run pipeline"
Write-Host "  psql -U postgres -d event_analytics - Access database"
Write-Host ""