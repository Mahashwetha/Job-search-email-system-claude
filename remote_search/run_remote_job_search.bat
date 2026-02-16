@echo off
REM =====================================================
REM Remote Job Search - Runs every 2 days at 12:00 PM CET
REM Fetches remote jobs from free APIs and sends email
REM =====================================================

REM Get the directory where this script is located
cd /d "%~dp0"

REM Run the Python script
python "%~dp0remote_job_search.py"

REM Log the execution
echo [%date% %time%] Remote job search completed >> "%~dp0job_search_log.txt"
