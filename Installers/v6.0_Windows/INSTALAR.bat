@echo off
REM ============================================================================
REM  BITTRADER WORKER - Instalador Automatico v6.0 - Windows
REM  Haz doble clic en este archivo para instalar.
REM  Compatible con Windows 10/11 (64-bit)
REM
REM  CAMBIOS v6.0:
REM  - Soporte completo de Futures: SHORT, leverage (1-10x), liquidacion,
REM    funding rates cada 8 horas.
REM  - Nuevo archivo config.py con fees de Spot y Futures.
REM  - GENOME_SIZE ampliado a 22 (direction + leverage).
REM  - Re-detecta URL del coordinator en cada inicio (LAN vs Tailscale).
REM ============================================================================
chcp 65001 >nul 2>&1
title Bittrader Worker Installer v6.0

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║       BITTRADER WORKER INSTALLER v6.0 - Windows         ║
echo  ║       + Futures: SHORT / Leverage / Funding             ║
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
    powershell -Command "$r = try { (Invoke-WebRequest -Uri '%WAN_URL%/api/status' -TimeoutSec 5 -UseBasicParsing).StatusCode } catch { 0 }; exit $r" >nul 2>&1
    if %ERRORLEVEL% GEQ 200 (
        set COORDINATOR_URL=%WAN_URL%
        echo   [OK] Tailscale detectado: %WAN_URL%
    ) else (
        echo.
        echo  ==============================================================
        echo    ERROR: SIN CONEXION AL COORDINATOR
        echo  ==============================================================
        echo.
        echo  No se pudo conectar al coordinator desde esta red.
        echo  Los workers necesitan Tailscale para conectarse remotamente.
        echo.
        echo  SOLUCION:
        echo    1. Instala Tailscale desde: https://tailscale.com/download
        echo    2. Inicia sesion con la cuenta que Ender te invite
        echo    3. Una vez conectado, vuelve a ejecutar INSTALAR.bat
        echo.
        echo  (Si estas en casa de Ender, verifica que estes en su WiFi^)
        echo.
        pause
        exit /b 1
    )
)

REM ── 2. Auto-detectar CPUs ────────────────────────────────────────────────
echo [2/7] Detectando CPUs...
for /f "tokens=2 delims==" %%i in ('wmic cpu get NumberOfLogicalProcessors /value 2^>nul ^| find "="') do set TOTAL_CPUS=%%i
set TOTAL_CPUS=%TOTAL_CPUS: =%
if "%TOTAL_CPUS%"=="" set TOTAL_CPUS=4
set /a NUM_WORKERS=%TOTAL_CPUS% - 2
if %NUM_WORKERS% LSS 1 set NUM_WORKERS=1
echo   CPUs: %TOTAL_CPUS% - Lanzando %NUM_WORKERS% workers

REM ── 3. Crear directorio de trabajo ──────────────────────────────────────
echo [3/7] Preparando directorio %WORK_DIR% ...
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
if not exist "%WORK_DIR%\logs" mkdir "%WORK_DIR%\logs"
if not exist "%WORK_DIR%\data" mkdir "%WORK_DIR%\data"
cd /d "%WORK_DIR%"

REM ── 4. Verificar / Instalar Python ──────────────────────────────────────
echo [4/7] Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Python no encontrado. Descargando instalador...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo   Instalando Python 3.11...
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    del "%TEMP%\python_installer.exe"
    set "PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python311;%USERPROFILE%\AppData\Local\Programs\Python\Python311\Scripts;%PATH%"
)
python --version
echo   [OK] Python listo

REM ── 5. Descargar archivos desde GitHub ──────────────────────────────────
echo [5/7] Descargando archivos desde GitHub...
for %%f in (crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py config.py) do (
    echo   Descargando %%f...
    powershell -Command "try { Invoke-WebRequest -Uri '%GITHUB_RAW%/%%f' -OutFile '%%f' -UseBasicParsing } catch { exit 1 }"
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: No se pudo descargar %%f. Verifica tu conexion.
        pause & exit /b 1
    )
)

if not exist "venv" (
    echo   Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install requests numpy numba pandas -q
python -c "import numba; print('  OK Numba ' + numba.__version__)"

REM ── 6. Crear scripts auxiliares ─────────────────────────────────────────
echo [6/7] Creando scripts...

REM config.env - sin URL hardcodeada (se detecta en cada inicio)
(
echo NUM_WORKERS=%NUM_WORKERS%
echo USE_RAY=false
echo PYTHONUNBUFFERED=1
echo INSTALLER_VERSION=6.0
echo LAN_URL=%LAN_URL%
echo WAN_URL=%WAN_URL%
) > config.env

REM ── start_workers.bat: RE-DETECTA URL en cada inicio ──
(
echo @echo off
echo cd /d "%%USERPROFILE%%\crypto_worker"
echo call venv\Scripts\activate.bat
echo.
echo REM Re-detectar coordinator URL en cada inicio
echo set COORDINATOR_URL=%WAN_URL%
echo powershell -Command "$r = try { (Invoke-WebRequest -Uri '%LAN_URL%/api/status' -TimeoutSec 3 -UseBasicParsing).StatusCode } catch { 0 }; exit $r" >nul 2>&1
echo if %%ERRORLEVEL%% GEQ 200 (
echo     set COORDINATOR_URL=%LAN_URL%
echo     echo   Red local detectada: %LAN_URL%
echo ) else (
echo     echo   Tailscale: %WAN_URL%
echo )
echo.
echo set NUM_WORKERS=%NUM_WORKERS%
echo set USE_RAY=false
echo set PYTHONUNBUFFERED=1
echo echo Iniciando %%NUM_WORKERS%% workers - %%COORDINATOR_URL%%...
echo for /L %%%%i in (1,1,%%NUM_WORKERS%%) do (
echo     start "BitWorker_%%%%i" /B cmd /c "set WORKER_INSTANCE=%%%%i ^& set COORDINATOR_URL=%%COORDINATOR_URL%% ^& python -u crypto_worker.py ^>^> logs\worker_%%%%i.log 2^>^&1"
echo     echo   Worker %%%%i iniciado
echo     timeout /t 2 /nobreak ^>nul
echo )
echo echo OK %%NUM_WORKERS%% workers iniciados.
) > start_workers.bat

(
echo @echo off
echo taskkill /F /FI "WINDOWTITLE eq BitWorker_*" /IM python.exe 2^>nul
echo powershell -Command "Get-Process python -ErrorAction SilentlyContinue ^| Where-Object {$_.CommandLine -like '*crypto_worker*'} ^| Stop-Process -Force" 2^>nul
echo echo OK Workers detenidos
) > stop_workers.bat

(
echo @echo off
echo echo ==============================
echo echo   BITTRADER WORKER STATUS v6.0
echo echo ==============================
echo for /f %%c in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2^>nul ^| find /c "python"') do echo   Workers activos: %%c
echo echo.
echo for %%i in (1 2 3 4 5 6 7 8) do (
echo     if exist "logs\worker_%%i.log" powershell -Command "Write-Host '  W%%i:'; Get-Content 'logs\worker_%%i.log' -Tail 1"
echo )
) > status.bat

(
echo @echo off
echo echo Actualizando archivos desde GitHub...
echo set GITHUB_RAW=https://raw.githubusercontent.com/enderjnets/Coinbase-Cripto-Trader-Claude/main
echo for %%f in (crypto_worker.py numba_backtester.py backtester.py dynamic_strategy.py strategy_miner.py config.py) do (
echo     powershell -Command "Invoke-WebRequest -Uri '%%GITHUB_RAW%%/%%f' -OutFile '%%f' -UseBasicParsing"
echo     echo   OK %%f
echo )
echo echo OK Actualizacion completada. Reinicia los workers.
echo pause
) > update.bat

REM ── 7. Configurar auto-inicio con Task Scheduler ────────────────────────
echo [7/7] Configurando inicio automatico...

(
echo @echo off
echo cd /d "%%USERPROFILE%%\crypto_worker"
echo call start_workers.bat
) > launcher.bat

schtasks /delete /tn "BittraderWorkers" /f >nul 2>&1
schtasks /create /tn "BittraderWorkers" /tr "\"%WORK_DIR%\launcher.bat\"" /sc onlogon /rl highest /f >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] Tarea programada creada
) else (
    echo   [WARN] Requiere permisos de administrador para auto-inicio
)

REM ── Iniciar workers ahora ───────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║          OK  INSTALACION COMPLETADA v6.0                ║
echo  ║       Futures: SHORT / Leverage / Funding               ║
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
echo   Los workers se iniciaran automaticamente al iniciar sesion.
echo.
pause
