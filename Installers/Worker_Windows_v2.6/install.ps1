# Bittrader Worker Installer v2.6 - Windows Edition
# PowerShell script for installing Ray Worker on Windows
# Requires: Windows 10/11, PowerShell 5.1+

#Requires -Version 5.1

# Enable strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param(
        [string]$Step,
        [string]$Message
    )
    Write-Host "[$Step] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

Write-Header "BITTRADER WORKER INSTALLER v2.6 - WINDOWS EDITION"

Write-ColorOutput "Professional Ray Worker for Windows" -Color Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-ColorOutput "ERROR: This script must be run as Administrator" -Color Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

# Configuration
$INSTALL_DIR = "$env:USERPROFILE\.bittrader_worker"
$SCRIPT_DIR = $PSScriptRoot

# ============================================================
# 1. CHECK WINDOWS VERSION
# ============================================================
Write-Step "1/8" "Checking Windows version..."

$osVersion = [System.Environment]::OSVersion.Version
if ($osVersion.Major -lt 10) {
    Write-ColorOutput "ERROR: Windows 10 or higher required" -Color Red
    Write-Host "Your version: Windows $($osVersion.Major).$($osVersion.Minor)"
    exit 1
}

Write-ColorOutput "   OK Windows $($osVersion.Major).$($osVersion.Minor)" -Color Green

# ============================================================
# 2. CHECK/INSTALL PYTHON 3.9.6
# ============================================================
Write-Step "2/8" "Checking Python 3.9.6..."

$pythonCmd = $null
$pythonPaths = @(
    "C:\Python39\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe",
    "$env:ProgramFiles\Python39\python.exe"
)

foreach ($path in $pythonPaths) {
    if (Test-Path $path) {
        $version = & $path --version 2>&1 | Select-String -Pattern "(\d+\.\d+\.\d+)" | ForEach-Object { $_.Matches.Value }
        if ($version -eq "3.9.6") {
            $pythonCmd = $path
            Write-ColorOutput "   OK Found Python 3.9.6 at: $path" -Color Green
            break
        }
    }
}

if (-not $pythonCmd) {
    Write-ColorOutput "   Python 3.9.6 not found. Installing..." -Color Yellow

    $pythonInstaller = "$env:TEMP\python-3.9.6-amd64.exe"
    $pythonUrl = "https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe"

    Write-Host "   Downloading Python 3.9.6 (may take 2-3 minutes)..."
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
        Write-ColorOutput "   OK Download completed" -Color Green
    } catch {
        Write-ColorOutput "ERROR: Failed to download Python" -Color Red
        Write-Host "Download manually from: $pythonUrl"
        exit 1
    }

    Write-Host "   Installing Python 3.9.6..."
    $installArgs = "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0"
    Start-Process -FilePath $pythonInstaller -ArgumentList $installArgs -Wait

    Remove-Item $pythonInstaller -ErrorAction SilentlyContinue

    # Find newly installed Python
    $pythonCmd = "$env:LOCALAPPDATA\Programs\Python\Python39\python.exe"
    if (-not (Test-Path $pythonCmd)) {
        $pythonCmd = "C:\Python39\python.exe"
    }

    if (Test-Path $pythonCmd) {
        Write-ColorOutput "   OK Python 3.9.6 installed successfully" -Color Green
    } else {
        Write-ColorOutput "ERROR: Python installation failed" -Color Red
        exit 1
    }
}

Write-Host "   Using Python: $pythonCmd"

# ============================================================
# 3. GET HEAD NODE IP
# ============================================================
Write-Step "3/8" "Configuring cluster connection..."

$HEAD_IP = $null
$configFile = "$INSTALL_DIR\config.env"

# Check for existing configuration
if (Test-Path $configFile) {
    $config = Get-Content $configFile | ConvertFrom-StringData
    $HEAD_IP = $config.HEAD_IP

    Write-Host "   Existing configuration found"
    Write-Host "   Head Node IP: $HEAD_IP"

    $keep = Read-Host "   Keep this configuration? (Y/n)"
    if ($keep -match "^[Nn]$") {
        $HEAD_IP = $null
    }
}

if (-not $HEAD_IP) {
    Write-Host ""
    Write-Host "   Enter the Head Node IP address (provided by administrator)"
    Write-Host "   • For local network: use local IP (e.g., 192.168.1.x)"
    Write-Host "   • For remote: use Tailscale IP (e.g., 100.x.x.x)"
    Write-Host ""

    $HEAD_IP = Read-Host "   Head Node IP"

    if (-not $HEAD_IP) {
        Write-ColorOutput "ERROR: Head Node IP is required" -Color Red
        exit 1
    }
}

Write-ColorOutput "   OK Head Node: $HEAD_IP" -Color Green

# ============================================================
# 4. CHECK TAILSCALE (OPTIONAL)
# ============================================================
Write-Step "4/8" "Checking network connectivity..."

# Test if Head Node is reachable
$pingResult = Test-Connection -ComputerName $HEAD_IP -Count 1 -Quiet

if ($pingResult) {
    Write-ColorOutput "   OK Head Node reachable" -Color Green
} else {
    Write-ColorOutput "   WARNING: Head Node not reachable" -Color Yellow
    Write-Host "   This may be normal if:"
    Write-Host "   • Head Node is not running yet"
    Write-Host "   • Tailscale VPN not connected"
    Write-Host "   • Firewall blocking ICMP"
    Write-Host ""

    # Check for Tailscale
    $tailscalePath = "$env:ProgramFiles\Tailscale\tailscale.exe"
    if (Test-Path $tailscalePath) {
        Write-Host "   Tailscale found. Checking status..."
        $tsStatus = & $tailscalePath status 2>&1

        if ($tsStatus -match "100\.") {
            Write-ColorOutput "   OK Tailscale connected" -Color Green
        } else {
            Write-ColorOutput "   WARNING: Tailscale not connected" -Color Yellow
            Write-Host "   Open Tailscale app and connect to continue"
            Read-Host "   Press Enter when connected"
        }
    } else {
        Write-Host "   Tailscale not found"
        Write-Host "   For remote connections, install from: https://tailscale.com/download/windows"
    }
}

# ============================================================
# 5. INSTALL RAY AND DEPENDENCIES
# ============================================================
Write-Step "5/8" "Installing Ray and dependencies..."

# Create installation directory
New-Item -ItemType Directory -Force -Path "$INSTALL_DIR\logs" | Out-Null

# Create virtual environment
$venvPath = "$INSTALL_DIR\venv"
Write-Host "   Creating virtual environment..."
& $pythonCmd -m venv $venvPath

$venvPython = "$venvPath\Scripts\python.exe"
$venvPip = "$venvPath\Scripts\pip.exe"

# Upgrade pip
Write-Host "   Upgrading pip..."
& $venvPip install --upgrade pip setuptools wheel --quiet

# Install Ray
Write-Host "   Installing Ray 2.51.2 (this may take several minutes)..."
& $venvPip install "ray[default]==2.51.2" --quiet

# Install dependencies
Write-Host "   Installing dependencies..."
& $venvPip install numpy pandas python-dotenv --quiet

# Verify installation
Write-Host "   Verifying Ray installation..."
$rayTest = & $venvPython -c "import ray; print(f'Ray {ray.__version__}')" 2>&1

if ($rayTest -match "Ray 2.51.2") {
    Write-ColorOutput "   OK $rayTest" -Color Green
} else {
    Write-ColorOutput "ERROR: Ray installation failed" -Color Red
    exit 1
}

# ============================================================
# 6. INSTALL WORKER DAEMON
# ============================================================
Write-Step "6/8" "Installing worker daemon..."

# Copy daemon script
Copy-Item "$SCRIPT_DIR\worker_daemon.ps1" "$INSTALL_DIR\" -Force

# Save configuration
$configContent = @"
HEAD_IP=$HEAD_IP
INSTALL_DATE=$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
VERSION=2.6
PYTHON_PATH=$venvPython
RAY_PATH=$venvPath\Scripts\ray.exe
"@

$configContent | Out-File -FilePath $configFile -Encoding UTF8

Write-ColorOutput "   OK Daemon installed" -Color Green

# ============================================================
# 7. CREATE WINDOWS SERVICE (OPTIONAL)
# ============================================================
Write-Step "7/8" "Configuring auto-start..."

$autoStart = Read-Host "   Enable auto-start on login? (Y/n)"

if ($autoStart -notmatch "^[Nn]$") {
    # Create scheduled task
    $taskName = "BittraderWorker"
    $taskDescription = "Bittrader Ray Worker - Automatically connects to cluster"

    # Remove existing task
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    # Create new task
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
        -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$INSTALL_DIR\worker_daemon.ps1`""

    $trigger = New-ScheduledTaskTrigger -AtLogOn

    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

    Register-ScheduledTask -TaskName $taskName -Description $taskDescription `
        -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null

    Write-ColorOutput "   OK Auto-start enabled (Scheduled Task)" -Color Green
} else {
    Write-ColorOutput "   Auto-start disabled" -Color Yellow
}

# ============================================================
# 8. CONFIGURE FIREWALL
# ============================================================
Write-Step "8/8" "Configuring firewall..."

try {
    $ruleName = "Bittrader Ray Worker"

    # Remove existing rule
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

    # Add new rule
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound `
        -Program $venvPython `
        -Action Allow `
        -Profile Any `
        -Description "Allow Bittrader Ray Worker communication" | Out-Null

    Write-ColorOutput "   OK Firewall rule added" -Color Green
} catch {
    Write-ColorOutput "   WARNING: Could not configure firewall (may require manual configuration)" -Color Yellow
}

# ============================================================
# INSTALLATION COMPLETE
# ============================================================
Write-Host ""
Write-Header "INSTALLATION COMPLETED SUCCESSFULLY"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "              WORKER CONFIGURATION" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Head Node IP:      $HEAD_IP"
Write-Host "   Port:              6379"
Write-Host "   Installation:      $INSTALL_DIR"
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "                 NEXT STEPS" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Verify installation: .\verify_worker.bat"
Write-Host "   2. Start worker now (if not auto-started)"
Write-Host "   3. To uninstall: .\uninstall.bat"
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "                    LOGS" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Worker log:  $INSTALL_DIR\logs\worker.log"
Write-Host ""

# Start now?
$startNow = Read-Host "Start worker now? (Y/n)"

if ($startNow -notmatch "^[Nn]$") {
    Write-Host ""
    Write-ColorOutput "Starting worker..." -Color Blue

    Start-Process PowerShell -ArgumentList "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$INSTALL_DIR\worker_daemon.ps1`"" -WindowStyle Hidden

    Start-Sleep -Seconds 3

    Write-ColorOutput "   OK Worker started in background" -Color Green
    Write-Host ""
    Write-Host "   Check status with: .\verify_worker.bat"
    Write-Host ""
}

Write-ColorOutput "Thank you for using Bittrader!" -Color Cyan
Write-Host ""
