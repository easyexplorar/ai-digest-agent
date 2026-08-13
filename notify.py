"""Windows 11 toast notification and output file writer."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def save_digest(digest_text: str, output_dir: str = "output") -> Path:
    """Save digest to a timestamped markdown file."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    filename = out / f"digest_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    filename.write_text(digest_text, encoding="utf-8")
    return filename


def send_windows_notification(title: str, message: str) -> None:
    """Send a Windows 11 toast notification via PowerShell."""
    # Truncate message to fit toast (256 chars)
    msg = message[:253] + "..." if len(message) > 256 else message
    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(8000, '{title}', '{msg}', [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 9
$notify.Dispose()
"""
    subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
