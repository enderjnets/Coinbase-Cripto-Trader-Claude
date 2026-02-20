#═══════════════════════════════════════════════════════════════════════════════
#  BITTRADER WORKER v4.0 - WINDOWS (AUTO-CONFIG)
#═══════════════════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "$env:USERPROFILE\crypto_worker"
$VERSION = "4.0"
$COORDINATOR_URL = "http://100.77.179.14:5001"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║    BITTRADER WORKER v4.0 - WINDOWS (AUTO-INSTALL)            ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║    4000x speedup • Multi-worker • Auto-start                 ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Coordinator: $COORDINATOR_URL" -ForegroundColor Green
Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Check/Install Python
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($version) {
            $major, $minor = $version.Split('.')
            if ([int]$major -ge 3 -and [int]$minor -ge 10) {
                $pythonCmd = $cmd
                Write-Host "   Found: $cmd ($version)" -ForegroundColor Green
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "   Python 3.10+ not found. Installing..." -ForegroundColor Yellow

    # Download Python installer
    $pythonUrl = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"

    Write-Host "   Downloading Python..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath

    Write-Host "   Installing Python (this may take a minute)..." -ForegroundColor Yellow
    Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait

    Remove-Item $installerPath -Force

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    $pythonCmd = "python"
    Write-Host "   Python installed" -ForegroundColor Green
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Create virtual environment
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "[2/6] Creating environment..." -ForegroundColor Yellow

if (Test-Path $INSTALL_DIR) {
    Remove-Item -Recurse -Force $INSTALL_DIR
}
New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null

Set-Location $INSTALL_DIR

& $pythonCmd -m venv venv
& .\venv\Scripts\Activate.ps1

& pip install --upgrade pip -q
& pip install numba pandas requests numpy -q

Write-Host "   Numba JIT installed (4000x speedup)" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Copy files
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "[3/6] Installing files..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$scriptDir\crypto_worker.py" $INSTALL_DIR
Copy-Item "$scriptDir\strategy_miner.py" $INSTALL_DIR
Copy-Item "$scriptDir\numba_backtester.py" $INSTALL_DIR
Copy-Item "$scriptDir\backtester.py" $INSTALL_DIR
Copy-Item "$scriptDir\dynamic_strategy.py" $INSTALL_DIR

New-Item -ItemType Directory -Path "$INSTALL_DIR\data" -Force | Out-Null
if (Test-Path "$scriptDir\data\BTC-USD_FIVE_MINUTE.csv") {
    Copy-Item "$scriptDir\data\BTC-USD_FIVE_MINUTE.csv" "$INSTALL_DIR\data\"
}

# Config
@"
COORDINATOR_URL=$COORDINATOR_URL
VERSION=$VERSION
"@ | Out-File -FilePath "$INSTALL_DIR\config.env" -Encoding UTF8

@"
class Config:
    TRADING_FEE_MAKER = 0.4
    TRADING_FEE_TAKER = 0.6
"@ | Out-File -FilePath "$INSTALL_DIR\config.py" -Encoding UTF8

Write-Host "   Files installed" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Detect CPU and configure workers
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "[4/6] Configuring workers..." -ForegroundColor Yellow

$cpuCount = (Get-WmiObject Win32_Processor).NumberOfLogicalProcessors
if ($cpuCount -gt 16) { $numWorkers = 6 }
elseif ($cpuCount -gt 8) { $numWorkers = 4 }
elseif ($cpuCount -gt 4) { $numWorkers = 3 }
else { $numWorkers = 2 }

Write-Host "   CPUs: $cpuCount -> $numWorkers workers" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Create scripts
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "[5/6] Creating scripts..." -ForegroundColor Yellow

# Start script with sleep prevention
@"
@echo off
cd /d "$INSTALL_DIR"
set COORDINATOR_URL=$COORDINATOR_URL

echo Stopping existing workers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq crypto_worker*" 2>nul
timeout /t 2 /nobreak > nul

echo Starting $numWorkers workers...
echo [Coffee] Sleep prevention enabled

REM Prevent sleep while workers run (powercfg)
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0

for /L %%i in (1,1,$numWorkers) do (
    set WORKER_INSTANCE=%%i
    set NUM_WORKERS=$numWorkers
    start /B "" ".\venv\Scripts\python.exe" -u crypto_worker.py > worker_%%i.log 2>&1
    timeout /t 2 /nobreak > nul
)

echo.
echo Workers started! Check logs: type worker_1.log
echo [!] System will stay awake while workers are running
echo.
pause
"@ | Out-File -FilePath "$INSTALL_DIR\start.bat" -Encoding ASCII

# Stop script with sleep restore
@"
@echo off
echo Stopping workers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq crypto_worker*" 2>nul

REM Restore default sleep settings (30 min AC, 15 min battery)
powercfg /change standby-timeout-ac 30
powercfg /change standby-timeout-dc 15
powercfg /change hibernate-timeout-ac 60
powercfg /change hibernate-timeout-dc 30

echo Workers stopped
echo [Zzz] Sleep settings restored to defaults
pause
"@ | Out-File -FilePath "$INSTALL_DIR\stop.bat" -Encoding ASCII

# Status script
@"
@echo off
echo === Worker Status ===
for /L %%i in (1,1,$numWorkers) do (
    echo Worker %%i:
    findstr /C:"Gen " "$INSTALL_DIR\worker_%%i.log" 2>nul | more +0 | findstr /N "." | findstr "^[0-9]*:" | sort /R | more +0 | findstr "."
)
pause
"@ | Out-File -FilePath "$INSTALL_DIR\status.bat" -Encoding ASCII

Write-Host "   Scripts created" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: Create startup shortcut
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "[6/6] Setting up autostart..." -ForegroundColor Yellow

$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = "$startupFolder\BittraderWorker.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$INSTALL_DIR\start.bat"
$shortcut.WorkingDirectory = $INSTALL_DIR
$shortcut.WindowStyle = 7  # Minimized
$shortcut.Save()

Write-Host "   Autostart enabled" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              INSTALLATION COMPLETE!                           ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "   Workers: $numWorkers" -ForegroundColor Cyan
Write-Host "   Location: $INSTALL_DIR" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting workers..." -ForegroundColor Yellow
Write-Host ""

Set-Location $INSTALL_DIR
Start-Process -FilePath ".\start.bat"
