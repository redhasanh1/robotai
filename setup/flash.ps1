# Compile + upload firmware\hand_esp32 to the ESP32, then open the console to check it booted.
#   powershell -ExecutionPolicy Bypass -File setup\flash.ps1            (auto-detects the port)
#   powershell -ExecutionPolicy Bypass -File setup\flash.ps1 -Port COM5
# If upload stalls at "Connecting....", hold the board's BOOT button until it starts writing.
param([string]$Port = "")

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Cli = Join-Path $HOME "Tools\arduino-cli\arduino-cli.exe"
Set-Location $Repo

if (-not $Port) {
    $boards = & $Cli board list --format json | ConvertFrom-Json
    $list = if ($boards.detected_ports) { $boards.detected_ports } else { $boards }
    $serial = @($list | Where-Object { $_.port.protocol -eq "serial" -and $_.port.address -ne "COM1" })
    if ($serial.Count -eq 0) {
        Write-Host "No ESP32 found. Is the USB cable a data cable? Is the driver installed? (setup\drivers.md)" -ForegroundColor Red
        exit 1
    }
    $Port = $serial[0].port.address
    Write-Host "Using $Port ($($serial[0].port.label))"
}

& $Cli compile --fqbn esp32:esp32:esp32 firmware\hand_esp32
& $Cli upload --fqbn esp32:esp32:esp32 -p $Port firmware\hand_esp32
Write-Host "`nUploaded. Opening the console - you should see 'BOOT hand-esp32 0.1' (press EN/RST if not)." -ForegroundColor Green
.venv\Scripts\python.exe tools\console.py $Port
