@echo off
REM =====================================================
REM Daily Job Search Agent - Runs at 11:00 AM CET
REM Reads Excel tracker and sends compact email
REM =====================================================

REM Get the directory where this script is located
cd /d "%~dp0"

REM Run the Python script
python "%~dp0daily_job_search.py"

REM Log the execution
echo [%date% %time%] Job search completed >> "%~dp0job_search_log.txt"
