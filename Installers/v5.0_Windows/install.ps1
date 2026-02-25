# ============================================================================
# Bittrader Worker Installer v5.0 - Windows PowerShell
# Fecha: 2026-02-24
# Uso: powershell -ExecutionPolicy Bypass -File install.ps1
# ============================================================================

param(
    [string]$CoordinatorUrl = "http://100.77.179.14:5001",
    [int]$NumWorkers = 4
)

$WorkDir = "$env:USERPROFILE\crypto_worker"

Write-Host "=========================================="
Write-Host "  Bittrader Worker Installer v5.0"
Write-Host "=========================================="
Write-Host ""
Write-Host "Coordinator: $CoordinatorUrl"
Write-Host "Workers: $NumWorkers"
Write-Host "Directory: $WorkDir"
Write-Host ""

# Crear directorio
Write-Host "Creando directorio..."
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
Set-Location $WorkDir

# Copiar archivos
Write-Host "Copiando archivos..."
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Copy-Item "$scriptDir\crypto_worker.py" -Destination . -Force
Copy-Item "$scriptDir\strategy_miner.py" -Destination . -Force
Copy-Item "$scriptDir\numba_backtester.py" -Destination . -Force
Copy-Item "$scriptDir\backtester.py" -Destination . -Force
Copy-Item "$scriptDir\dynamic_strategy.py" -Destination . -Force

# Verificar Python
Write-Host "Verificando Python..."
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python encontrado: $pythonVersion"
} catch {
    Write-Host "Python no encontrado. Instalando..."
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
}

# Crear entorno virtual
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual..."
    python -m venv venv
}

# Activar y instalar dependencias
Write-Host "Instalando dependencias..."
& ".\venv\Scripts\activate.ps1"
pip install --upgrade pip
pip install requests numpy numba pandas

# Verificar Numba
Write-Host "Verificando Numba JIT..."
python -c "import numba; print(f'Numba version: {numba.__version__}')"

# Crear script de inicio
$startScript = @"
`$env:COORDINATOR_URL = "$CoordinatorUrl"
`$env:NUM_WORKERS = "$NumWorkers"
`$env:USE_RAY = "false"
`$env:PYTHONUNBUFFERED = "1"

Set-Location "$WorkDir"
& ".\venv\Scripts\activate.ps1"

Write-Host "Iniciando $NumWorkers workers..."

for (`$i = 1; `$i -le $NumWorkers; `$i++) {
    `$env:WORKER_INSTANCE = `$i
    Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-u", "crypto_worker.py" -RedirectStandardOutput "worker_`$i.log" -RedirectStandardError "worker_`$i_err.log"
    Write-Host "Worker `$i iniciado"
    Start-Sleep -Seconds 2
}

Write-Host "`$NumWorkers workers iniciados"
"@

$startScript | Out-File -FilePath "start_workers.ps1" -Encoding UTF8

# Crear script de parada
$stopScript = @"
Write-Host "Deteniendo workers..."
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { `$_.MainWindowTitle -like "*worker*" -or `$_.CommandLine -like "*crypto_worker*" } | Stop-Process -Force
Write-Host "Workers detenidos"
"@

$stopScript | Out-File -FilePath "stop_workers.ps1" -Encoding UTF8

# Crear acceso directo en escritorio
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Bittrader Worker.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$WorkDir\start_workers.ps1`""
$Shortcut.WorkingDirectory = $WorkDir
$Shortcut.Description = "Iniciar Bittrader Workers"
$Shortcut.Save()

Write-Host ""
Write-Host "=========================================="
Write-Host "  Instalacion completada!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Para iniciar workers:"
Write-Host "  cd $WorkDir"
Write-Host "  .\start_workers.ps1"
Write-Host ""
Write-Host "Tambien puedes usar el acceso directo en el escritorio"
Write-Host ""
