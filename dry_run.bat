@echo off
echo ===================================================
echo [Creative Radar] Running Dry Run Simulation...
echo (Simulates ingest without sending live Telegram alerts)
echo ===================================================
py -3.12 main.py --dry-run
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Dry run failed with code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [SUCCESS] Dry run simulation finished successfully!
pause
