# Registers the AI Digest Agent as a Windows Task Scheduler job.
# Run this script once as Administrator.
# Default: runs Mon–Fri at 10:00 local (CST/UTC+8), with a logon backup trigger.

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe  = (Get-Command py).Source
$Script     = Join-Path $ProjectDir "run_digest.py"
$TaskName   = "AI-Digest-Agent"
$RunAt      = "10:00"

# China Standard Time is UTC+8. Windows Task Scheduler fires at local system time,
# so this assumes the machine clock is set to CST (UTC+8). If your system is in a
# different timezone, adjust $RunAt to the equivalent local time.
$Action  = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$Script`" --scheduled" -WorkingDirectory $ProjectDir
$Trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 `
           -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $RunAt
# Backup for days the PC was off or nobody was signed in at 10:00. --scheduled
# makes run_digest.py skip weekends, logons before 10:00, and days already sent.
$LogonTrigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$LogonTrigger.Delay = "PT2M"
# 30 min: a normal run takes ~3 min, but arXiv retries alone have taken ~7 min,
# and on Fridays the weekly rollup runs after the daily digest in the same run.
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
            -StartWhenAvailable -MultipleInstances IgnoreNew

# S4U = "run whether user is logged on or not" without storing a password, so
# the 10:00 run still fires if Windows is up but nobody has signed in yet.
# Trade-off: no desktop session, so toast notifications won't show.
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger,$LogonTrigger -Settings $Settings -Principal $Principal -Force

# Keep Task Scheduler run history so a missed run can be traced afterwards.
wevtutil set-log Microsoft-Windows-TaskScheduler/Operational /enabled:true

Write-Host "Task '$TaskName' registered — runs Mon-Fri at $RunAt local (CST/UTC+8), plus a logon backup."
Write-Host "To run immediately: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:          Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
