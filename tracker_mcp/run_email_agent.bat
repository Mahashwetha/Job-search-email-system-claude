@echo off
REM =====================================================
REM Job tracker email agent - checks replies to the daily/remote digests
REM Scheduled every 30 min (task "JobTrackerEmailAgent", launched hidden via run_email_agent_hidden.vbs)
REM Logs: tracker_mcp\logs\agent_YYYYMMDD.log
REM =====================================================
cd /d "%~dp0.."
"%~dp0.venv\Scripts\python.exe" "%~dp0email_agent.py" %*
