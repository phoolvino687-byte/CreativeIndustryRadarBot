@echo off
echo ===================================================
echo [Creative Radar] Starting Local Dashboard Server...
echo Opening: http://localhost:8000
echo Press Ctrl+C in this terminal window to stop the server.
echo ===================================================
start http://localhost:8000
py -3.12 -m http.server 8000
