# Setup Daily Job Search Scheduled Task
# Run this script as Administrator

Write-Host "Setting up Daily Job Search scheduled task..." -ForegroundColor Cyan

# Task details
$taskName = "DailyJobSearch"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir "run_daily_job_search.bat"
$time = "11:00"

# Delete existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction -Execute $scriptPath

# Create trigger (daily at 10:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At $time

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# Register the task
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Daily job search email - reads Excel tracker and sends compact email at 11:00 AM CET" `
    -User $env:USERNAME `
    -RunLevel Highest

Write-Host "`nScheduled task created successfully!" -ForegroundColor Green
Write-Host "Task Name: $taskName" -ForegroundColor Green
Write-Host "Run Time: Daily at $time" -ForegroundColor Green
Write-Host "Script: $scriptPath" -ForegroundColor Green

Write-Host "`nTo verify, open Task Scheduler (taskschd.msc) and look for '$taskName'" -ForegroundColor Cyan

# Display next run time
$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Host "`nNext Run Time: $($info.NextRunTime)" -ForegroundColor Yellow
