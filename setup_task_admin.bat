@echo off
REM =====================================================
REM Setup Daily Job Search Scheduled Task
REM RIGHT-CLICK THIS FILE AND SELECT "Run as administrator"
REM =====================================================

echo Setting up Daily Job Search scheduled task...
echo.

REM Delete existing task if it exists (ignore errors)
schtasks /delete /tn "DailyJobSearch" /f >nul 2>&1

REM Create new scheduled task (using current script location)
schtasks /create ^
  /tn "DailyJobSearch" ^
  /tr "%~dp0run_daily_job_search.bat" ^
  /sc daily ^
  /st 11:00 ^
  /rl HIGHEST ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Scheduled task created.
    echo ========================================
    echo Task Name: DailyJobSearch
    echo Run Time: Daily at 11:00 AM
    echo Script: run_daily_job_search.bat
    echo.
    echo Next run: Tomorrow at 11:00 AM
    echo.
    echo To verify: Press Win+R, type taskschd.msc
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: Failed to create scheduled task
    echo ========================================
    echo Please make sure you ran this file as Administrator
    echo Right-click setup_task_admin.bat and select "Run as administrator"
    echo ========================================
)

echo.
pause
