@echo off
REM ============================================================================
REM  BITTRADER WORKER - Instalador Automatico v5.1 - Windows
REM  Haz doble clic en este archivo para instalar.
REM  Compatible con Windows 10/11 (64-bit)
REM ============================================================================
chcp 65001 >nul 2>&1
title Bittrader Worker Installer v5.1

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║       BITTRADER WORKER INSTALLER v5.1 - Windows         ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

set WORK_DIR=%USERPROFILE%\crypto_worker
set GITHUB_RAW=https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main
set LAN_URL=http://10.0.0.232:5001
set WAN_URL=http://100.77.179.14:5001

REM ── 1. Auto-detectar red (LAN vs WAN) ──────────────────────────────────
echo [1/7] Detectando red...
powershell -Command "$r = try { (Invoke-WebRequest -Uri '%LAN_URL%/api/status' -TimeoutSec 2 -UseBasicParsing).StatusCode } catch { 0 }; exit $r" >nul 2>&1
if %ERRORLEVEL% GEQ 200 (
    set COORDINATOR_URL=%LAN_URL%
    echo   [OK] Red local detectada: %LAN_URL%
) else (
    set COORDINATOR_URL=%WAN_URL%
    echo   [->] Red externa (Tailscale): %WAN_URL%
)

REM ── 2. Auto-detectar CPUs ────────────────────────────────────────────────
echo [2/7] Detectando CPUs...
for /f "tokens=2 delims==" %%i in ('wmic cpu get NumberOfLogicalProcessors /value 2^>nul ^| find "="') do set TOTAL_CPUS=%%i
set TOTAL_CPUS=%TOTAL_CPUS: =%
if "%TOTAL_CPUS%"=="" set TOTAL_CPUS=4
set /a NUM_WORKERS=%TOTAL_CPUS% - 2
if %NUM_WORKERS% LSS 1 set NUM_WORKERS=1
echo   CPUs: %TOTAL_CPUS% -> Lanzando %NUM_WORKERS% workers

REM ── 3. Crear directorio de trabajo ──────────────────────────────────────
echo [3/7] Preparando directorio %WORK_DIR% ...
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"
mkdir logs 2>nul

REM ── 4. Verificar / Instalar Python ──────────────────────────────────────
echo [4/7] Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Python no encontrado. Descargando instalador...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo   Instalando Python 3.11 (puede tardar unos minutos)...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del "%TEMP%\python_installer.exe"
    REM Actualizar PATH
    set "PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python311;%USERPROFILE%\AppData\Local\Programs\Python\Python311\Scripts;%PATH%"
)
python --version
echo   [OK] Python listo

REM ── 5. Descargar archivos desde GitHub ──────────────────────────────────
echo [5/7] Descargando archivos desde GitHub...
set FILES=crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py
for %%f in (%FILES%) do (
    echo   Descargando %%f...
    powershell -Command "try { Invoke-WebRequest -Uri '%GITHUB_RAW%/%%f' -OutFile '%%f' -UseBasicParsing; Write-Host '    OK' } catch { Write-Host '    ERROR: ' $_.Exception.Message; exit 1 }"
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: No se pudo descargar %%f. Verifica tu conexion.
        pause
        exit /b 1
    )
)

REM Crear entorno virtual
if not exist "venv" (
    echo   Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo   Instalando paquetes Python...
pip install --upgrade pip -q
pip install requests numpy numba pandas -q
python -c "import numba; print('  OK Numba ' + numba.__version__)"

REM ── 6. Crear scripts auxiliares ─────────────────────────────────────────
echo [6/7] Creando scripts...

REM Guardar config
(
echo COORDINATOR_URL=%COORDINATOR_URL%
echo NUM_WORKERS=%NUM_WORKERS%
echo USE_RAY=false
echo PYTHONUNBUFFERED=1
echo INSTALLER_VERSION=5.1
) > config.env

REM Script de inicio
(
echo @echo off
echo cd /d "%%USERPROFILE%%\crypto_worker"
echo call venv\Scripts\activate.bat
echo set COORDINATOR_URL=%COORDINATOR_URL%
echo set NUM_WORKERS=%NUM_WORKERS%
echo set USE_RAY=false
echo set PYTHONUNBUFFERED=1
echo echo Iniciando %%NUM_WORKERS%% workers...
echo for /L %%%%i in (1,1,%%NUM_WORKERS%%) do (
echo     start "BitWorker_%%%%i" /B cmd /c "set WORKER_INSTANCE=%%%%i ^& python -u crypto_worker.py ^>^> logs\worker_%%%%i.log 2^>^&1"
echo     echo   Worker %%%%i iniciado
echo     timeout /t 2 /nobreak ^>nul
echo )
echo echo.
echo echo OK %%NUM_WORKERS%% workers iniciados.
) > start_workers.bat

REM Script de parada
(
echo @echo off
echo taskkill /F /FI "WINDOWTITLE eq BitWorker_*" /IM python.exe 2^>nul
echo powershell -Command "Get-Process python -ErrorAction SilentlyContinue ^| Where-Object {$_.CommandLine -like '*crypto_worker*'} ^| Stop-Process -Force"
echo echo OK Workers detenidos
) > stop_workers.bat

REM Script de estado
(
echo @echo off
echo echo ==============================
echo echo   BITTRADER WORKER STATUS
echo echo ==============================
echo for /f %%c in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2^>nul ^| find /c "python"') do echo   Workers activos: %%c
echo echo   Coordinator: %COORDINATOR_URL%
echo echo.
echo echo   Ultimos logs:
echo for %%i in (1 2 3 4 5 6 7 8) do (
echo     if exist "logs\worker_%%i.log" (
echo         echo   --- Worker %%i ---
echo         powershell -Command "Get-Content 'logs\worker_%%i.log' -Tail 2"
echo     )
echo )
) > status.bat

REM Script de actualización
(
echo @echo off
echo echo Actualizando archivos desde GitHub...
echo set GITHUB_RAW=https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main
echo for %%f in (crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py) do (
echo     powershell -Command "Invoke-WebRequest -Uri '%%GITHUB_RAW%%/%%f' -OutFile '%%f' -UseBasicParsing"
echo     echo   OK %%f
echo )
echo echo OK Actualizacion completada. Reinicia los workers.
echo pause
) > update.bat

REM ── 7. Configurar auto-inicio con Task Scheduler ────────────────────────
echo [7/7] Configurando inicio automatico (Task Scheduler)...

REM Crear script launcher para el servicio
(
echo @echo off
echo cd /d "%%USERPROFILE%%\crypto_worker"
echo call start_workers.bat
) > launcher.bat

REM Registrar tarea programada
schtasks /delete /tn "BittraderWorkers" /f >nul 2>&1
schtasks /create /tn "BittraderWorkers" /tr "\"%WORK_DIR%\launcher.bat\"" /sc onlogon /rl highest /f >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Tarea programada creada (se iniciara al iniciar sesion)
) else (
    echo   [WARN] No se pudo crear la tarea (puede requerir permisos de administrador)
)

REM ── Iniciar workers ahora ───────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║             OK  INSTALACION COMPLETADA                  ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo   Coordinator : %COORDINATOR_URL%
echo   Workers     : %NUM_WORKERS% workers
echo   Directorio  : %WORK_DIR%
echo.
echo   Iniciando workers...
call start_workers.bat
echo.
echo   Comandos utiles:
echo     Ver estado  : cd %%USERPROFILE%%\crypto_worker ^& status.bat
echo     Detener     : cd %%USERPROFILE%%\crypto_worker ^& stop_workers.bat
echo     Actualizar  : cd %%USERPROFILE%%\crypto_worker ^& update.bat
echo.
echo   Los workers se iniciaran automaticamente al iniciar sesion en Windows.
echo.
pause
