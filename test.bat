@echo off
echo ===================================================
echo [Creative Radar] Running Automated Test Suite...
echo ===================================================
py -3.12 -m pytest -v
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Tests failed! Review output above.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo [SUCCESS] All 35 tests passed!
pause
