# Bittrader Worker Daemon v2.6 - Windows Edition
# PowerShell daemon for persistent Ray Worker connection

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$INSTALL_DIR = "$env:USERPROFILE\.bittrader_worker"
$LOG_FILE = "$INSTALL_DIR\logs\worker.log"
$LOCK_FILE = "$INSTALL_DIR\worker_daemon.lock"

# Create logs directory
New-Item -ItemType Directory -Force -Path "$INSTALL_DIR\logs" | Out-Null

# Check if already running
if (Test-Path $LOCK_FILE) {
    $pid = Get-Content $LOCK_FILE
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Worker daemon already running (PID: $pid)"
        exit 1
    }
}

# Create lock file
$PID | Out-File -FilePath $LOCK_FILE

# Cleanup on exit
$cleanup = {
    Remove-Item $LOCK_FILE -ErrorAction SilentlyContinue
}
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action $cleanup | Out-Null

# Load configuration
$configFile = "$INSTALL_DIR\config.env"
if (-not (Test-Path $configFile)) {
    Write-Host "ERROR: config.env not found"
    exit 1
}

$config = Get-Content $configFile | ConvertFrom-StringData
$HEAD_IP = $config.HEAD_IP
$PYTHON_PATH = $config.PYTHON_PATH
$RAY_PATH = $config.RAY_PATH

# Logging function
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Add-Content -Path $LOG_FILE -Value $logMessage
    Write-Host $logMessage
}

Write-Log "================================================================"
Write-Log "    Worker Daemon v2.6 Starting (Windows)"
Write-Log "================================================================"
Write-Log ""
Write-Log "Configuration:"
Write-Log "  Head IP: $HEAD_IP"
Write-Log "  Python: $PYTHON_PATH"
Write-Log "  Ray: $RAY_PATH"
Write-Log ""

# Environment variables
$env:RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER = "1"
$env:RAY_ENABLE_IPV6 = "0"

# Get CPU count
$NUM_CPUS = (Get-WmiObject -Class Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum

Write-Log "CPUs available: $NUM_CPUS"

$retryCount = 0
$maxRetries = 999999

while ($retryCount -lt $maxRetries) {
    # Check connectivity to HEAD
    $pingResult = Test-Connection -ComputerName $HEAD_IP -Count 1 -Quiet

    if (-not $pingResult) {
        Write-Log "WARNING: Cannot reach Head Node ($HEAD_IP)"
        Write-Log "   Retrying in 30 seconds..."
        Start-Sleep -Seconds 30
        continue
    }

    # Check if Ray is already running
    $rayProcesses = Get-Process -Name "raylet" -ErrorAction SilentlyContinue

    if ($rayProcesses) {
        # Ray is running, check if healthy
        try {
            $healthCheck = & $PYTHON_PATH -c "import ray; ray.init(address='auto', ignore_reinit_error=True); print('OK')" 2>&1

            if ($healthCheck -match "OK") {
                Start-Sleep -Seconds 60
                continue
            } else {
                Write-Log "WARNING: Ray running but not connected. Restarting..."
                & $RAY_PATH stop 2>&1 | Out-Null
                Start-Sleep -Seconds 2
            }
        } catch {
            Write-Log "WARNING: Health check failed. Restarting..."
            & $RAY_PATH stop 2>&1 | Out-Null
            Start-Sleep -Seconds 2
        }
    }

    # Connect to cluster
    Write-Log "Connecting to $HEAD_IP:6379..."

    try {
        $output = & $RAY_PATH start --address="${HEAD_IP}:6379" --num-cpus=$NUM_CPUS 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Log "OK Connected to cluster with $NUM_CPUS CPUs"
            Write-Log "   $output"
        } else {
            Write-Log "ERROR: Connection failed"
            Write-Log "   $output"
            Write-Log "   Retrying in 30 seconds..."
            Start-Sleep -Seconds 30
            $retryCount++
            continue
        }
    } catch {
        Write-Log "ERROR: Exception during connection: $_"
        Start-Sleep -Seconds 30
        $retryCount++
        continue
    }

    # Monitor connection
    Start-Sleep -Seconds 60
}

Write-Log "ERROR: Maximum retry attempts reached. Exiting."
