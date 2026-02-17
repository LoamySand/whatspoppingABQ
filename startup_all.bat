@echo off
setlocal enabledelayedexpansion

REM Unified startup for whatspoppingABQ automation
cd /d C:\Users\lanee\Desktop\whatspoppingABQ
call venv\Scripts\activate.bat

echo ============================================
echo whatspoppingABQ Automation Startup
echo ============================================
echo.

REM Kill any existing processes
echo Cleaning up existing processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Prefect*" >nul 2>&1
timeout /t 3 /nobreak > nul

REM ============================================
REM Start Prefect Server
REM ============================================
echo [1/2] Starting Prefect server...
echo.

REM Delete old log
if exist prefect_server.log del prefect_server.log

REM Start server
start "Prefect Server" /MIN cmd /c "cd /d C:\Users\lanee\Desktop\whatspoppingABQ && venv\Scripts\activate.bat && prefect server start > prefect_server.log 2>&1"

echo Waiting for server to start...
set /a attempts=0
set /a max_attempts=30

:wait_for_server
set /a attempts+=1
timeout /t 2 /nobreak > nul

REM Check if server is responding
curl -s http://127.0.0.1:4200/api/health > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Server is ready! ^(attempt %attempts%/%max_attempts%^)
    goto server_ready
)

if %attempts% LSS %max_attempts% (
    echo Still waiting... ^(attempt %attempts%/%max_attempts%^)
    goto wait_for_server
) else (
    echo.
    echo ERROR: Server did not start after %max_attempts% attempts
    echo Check prefect_server.log for errors
    echo.
    pause
    exit /b 1
)

:server_ready
echo.

REM ============================================
REM Start Flows
REM ============================================
echo [2/2] Starting Prefect flows...
echo.

REM Delete old log
if exist prefect_flows.log del prefect_flows.log

REM Set API URL and start flows
start "Prefect Flows" /MIN cmd /c "cd /d C:\Users\lanee\Desktop\whatspoppingABQ && venv\Scripts\activate.bat && set PREFECT_API_URL=http://127.0.0.1:4200/api && python run_prefect_flows.py > prefect_flows.log 2>&1"

echo Waiting for flows to register...
timeout /t 10 /nobreak > nul

REM Check if flows process is still running
tasklist /FI "WINDOWTITLE eq Prefect Flows" 2>nul | find /I /N "cmd.exe" > nul
if %ERRORLEVEL% EQU 0 (
    echo Flows are running!
) else (
    echo.
    echo WARNING: Flows process may have exited
    echo Check prefect_flows.log for errors
    echo.
)

echo.
echo ============================================
echo Startup Complete
echo ============================================
echo.
echo Services:
echo   Server: http://localhost:4200
echo   Flows: Running in background
echo.
echo Logs:
echo   - prefect_server.log
echo   - prefect_flows.log
echo.
echo Check status: http://localhost:4200
echo.
timeout /t 10 /nobreak

endlocal