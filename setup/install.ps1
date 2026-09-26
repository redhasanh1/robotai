# PINN Humanoid - one-shot setup for the hand software on Windows.
# Run from the repo root in PowerShell:   powershell -ExecutionPolicy Bypass -File setup\install.ps1
# Safe to re-run: every step checks before installing. Installs nothing system-wide except what winget/uv put
# in your user profile. USB drivers are NOT installed here (they need admin) - see setup\drivers.md.

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $HOME "Tools"
$Cli = Join-Path $Tools "arduino-cli\arduino-cli.exe"
Set-Location $Repo

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }

Step "1/5 Python (uv + Python 3.12 venv in .venv)"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "No python on PATH - installing Python 3.12 with winget"
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "User") + ";" + $env:PATH
}
python -m pip install -q --upgrade uv
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m uv python install 3.12
    python -m uv venv --python 3.12 .venv
}

Step "2/5 Python packages (MuJoCo, OpenCV, pyserial, pytest, PyTorch with CUDA 12.6)"
python -m uv pip install --python .venv\Scripts\python.exe -r requirements.txt
python -m uv pip install --python .venv\Scripts\python.exe torch --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe -c "import torch, mujoco, cv2, serial; print('torch', torch.__version__, 'CUDA', torch.cuda.is_available(), '| mujoco', mujoco.__version__, '| opencv', cv2.__version__)"

Step "3/5 arduino-cli (compiles and uploads the ESP32 firmware, no Arduino IDE needed)"
if (-not (Test-Path $Cli)) {
    New-Item -ItemType Directory -Force (Split-Path $Cli) | Out-Null
    $zip = Join-Path $env:TEMP "arduino-cli.zip"
    Invoke-WebRequest "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath (Split-Path $Cli) -Force
}
& $Cli version

Step "4/5 ESP32 board support (esp32:esp32, ~1 GB download the first time)"
& $Cli config init --overwrite | Out-Null
& $Cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
& $Cli core update-index
$have = & $Cli core list | Select-String "esp32:esp32"
if (-not $have) { & $Cli core install esp32:esp32 }

Step "5/5 Check: compile firmware + run tests"
& $Cli compile --fqbn esp32:esp32:esp32 firmware\hand_esp32
.venv\Scripts\python.exe -m pytest -q

Write-Host "`nAll set. Next: plug in the ESP32 (see setup\drivers.md if no COM port shows up), then" -ForegroundColor Green
Write-Host "  powershell -ExecutionPolicy Bypass -File setup\flash.ps1" -ForegroundColor Green
