@echo off
echo ===================================================
echo [Creative Radar] Running Pipeline...
echo ===================================================
py -3.12 main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Pipeline failed with code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [SUCCESS] Creative Radar run finished!
pause
