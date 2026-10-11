# Registers the AI Digest Agent as a Windows Task Scheduler job.
# Run this script once as Administrator.
# Default: runs Mon–Fri at 10:00 local (CST/UTC+8).

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe  = (Get-Command py).Source
$Script     = Join-Path $ProjectDir "run_digest.py"
$TaskName   = "AI-Digest-Agent"
$RunAt      = "10:00"

# China Standard Time is UTC+8. Windows Task Scheduler fires at local system time,
# so this assumes the machine clock is set to CST (UTC+8). If your system is in a
# different timezone, adjust $RunAt to the equivalent local time.
$Action  = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$Script`"" -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 `
           -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $RunAt
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
            -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -RunLevel Limited -Force

Write-Host "Task '$TaskName' registered — runs Mon-Fri at $RunAt local (CST/UTC+8)."
Write-Host "To run immediately: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:          Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
