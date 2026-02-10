@echo off
REM ################################################################################
REM # 🧬 AUTO-INSTALLER WORKER - WINDOWS BATCH SCRIPT
REM # Instalador autónomo para Windows
REM #
REM # Este script configura TODO automáticamente:
REM # - Detecta Python instalado
REM # - Clona/actualiza el proyecto
REM # - Configura workers según CPUs
REM # - Configura auto-arranque al reiniciar
REM # - Conecta automáticamente al coordinator
REM #
REM # Uso: .\install_worker.bat [COORDINATOR_URL]
REM ################################################################################

setlocal EnableDelayedExpansion

REM ═══════════════════════════════════════════════════════════════════════════════
REM COLORS
REM ═══════════════════════════════════════════════════════════════════════════════
for /f "delims=#" %%a in ('"prompt #$E# & for /b"2> nul') do set "ESC=%%a"
set "GREEN=%ESC%[0;32m"
set "YELLOW=%ESC%[1;33m"
set "BLUE=%ESC%[0;34m"
set "CYAN=%ESC%[0;36m"
set "RED=%ESC%[0;31m"
set "NC=%ESC%[0m"

REM ═══════════════════════════════════════════════════════════════════════════════
REM CONFIGURATION
REM ═══════════════════════════════════════════════════════════════════════════════
set "REPO_URL=https://github.com/enderjnets/Coinbase-Cripto-Trader-Claude.git"
set "COORDINATOR_URL=%~1"
if "%COORDINATOR_URL%"=="" set "COORDINATOR_URL=http://100.77.179.14:5001"
set "PROJECT_DIR=%USERPROFILE%\Coinbase-Cripto-Trader-Claude"
set "WORKER_DIR=%USERPROFILE%\.crypto_worker"
set "LOG_FILE=%WORKER_DIR%\install.log"
set "INSTALL_SCRIPT=%WORKER_DIR%\start_workers.bat"

REM ═══════════════════════════════════════════════════════════════════════════════
REM FUNCTIONS
REM ═══════════════════════════════════════════════════════════════════════════════
:log
echo [%date% %time%] %~1 >> "%LOG_FILE%"
echo %~1
goto :eof

:log_color
echo [%date% %time%] %~2 >> "%LOG_FILE%"
echo %~2
goto :eof

:detect_os
echo.
call :log_color "🔍 Detectando sistema operativo..." "BLUE"
for /f "tokens=2 delims=[]" %%a in ('ver') do set "OS_VERSION=%%a"
echo %OS_VERSION% | findstr /i "Windows" > nul
if errorlevel 0 (
    set "OS_TYPE=windows"
    set "OS_NAME=Windows"
)
call :log_color "✅ Sistema: %OS_NAME%" "GREEN"
goto :eof

:detect_cpu_cores
echo.
call :log_color "🔍 Detectando CPUs..." "BLUE"
wmic CPU Get NumberOfCores /value 2>nul | findstr /i "NumberOfCores=" > cores.tmp
set /a CPU_CORES=0
for /f "tokens=2 delims==" %%a in (cores.tmp) do set /a CPU_CORES+=%%a
del cores.tmp 2>nul
if "%CPU_CORES%"=="0" set "CPU_CORES=4"
set /a WORKERS_COUNT=%CPU_CORES%-2
if %WORKERS_COUNT% LSS 1 set WORKERS_COUNT=1
call :log_color "✅ CPU cores: %CPU_CORES% - Workers a iniciar: %WORKERS_COUNT%" "GREEN"
goto :eof

:setup_directories
echo.
call :log_color "📁 Creando directorios..." "BLUE"
mkdir "%WORKER_DIR%" 2>nul
mkdir "%PROJECT_DIR%" 2>nul
call :log_color "✅ Directorios creados" "GREEN"
goto :eof

:install_dependencies
echo.
call :log_color "📦 Verificando dependencias..." "BLUE"

REM Check Python
python --version 2>nul > nul
if errorlevel 1 (
    call :log_color "⚠️  Python no encontrado. Descargando..." "YELLOW"
    echo Descarga Python desde: https://python.org/downloads/
    echo Depois ejecuta este script nuevamente.
    pause
    exit /b 1
)

REM Check git
git --version 2>nul > nul
if errorlevel 1 (
    call :log_color "⚠️  Git no encontrado. Descargando..." "YELLOW"
    echo Descarga Git desde: https://git-scm.com/download/win
    echo Depois ejecuta este script nuevamente.
    pause
    exit /b 1
)

REM Install Python packages
call :log_color "📦 Instalando paquetes Python..." "YELLOW"
python -m pip install requests pandas numpy --quiet 2>nul
call :log_color "✅ Dependencias instaladas" "GREEN"
goto :eof

:clone_or_update_project
echo.
call :log_color "📥 Configurando proyecto..." "BLUE"
if exist "%PROJECT_DIR%\.git" (
    call :log "📥 Proyecto ya existe, actualizando..."
    cd /d "%PROJECT_DIR%"
    git pull origin main --quiet 2>nul || git pull origin main 2>nul
) else (
    call :log "📥 Clonando proyecto..."
    git clone "%REPO_URL%" "%PROJECT_DIR%"
)
call :log_color "✅ Proyecto en: %PROJECT_DIR%" "GREEN"
goto :eof

:create_startup_script
echo.
call :log_color "🚀 Creando script de inicio..." "YELLOW"

REM Create start script
(
    echo @echo off
    echo REM ################################################################################
    echo REM # SCRIPT DE INICIO DE WORKERS - AUTO-GENERADO
    echo REM ################################################################################
    echo setlocal EnableDelayedExpansion
    echo cd /d "%PROJECT_DIR%"
    echo taskkill /f /im python.exe 2^>nul ^>nul
    echo timeout /t 2 /nobreak ^>nul
    echo for %%%%i in ^(1 2 3 4^) do ^(
    echo     start /B python.exe "%%PROJECT_DIR%%\crypto_worker.py" "%COORDINATOR_URL%" ^> "%WORKER_DIR%%\worker_%%%%i.log" 2^>^&1
    echo ^)
    echo echo Workers iniciados: %WORKERS_COUNT%
) > "%INSTALL_SCRIPT%"

call :log_color "✅ Script de inicio creado" "GREEN"
goto :eof

:setup_auto_start
echo.
call :log_color "⏰ Configurando auto-arranque..." "YELLOW"

REM Create startup folder shortcut or registry entry
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "CryptoWorker" /t REG_SZ /d "\"%INSTALL_SCRIPT%\"" /f > nul 2>&1

call :log_color "✅ Auto-arranque configurado (Registro de Windows)" "GREEN"
goto :eof

:start_workers
echo.
call :log_color "🚀 Iniciando workers..." "YELLOW"

cd /d "%PROJECT_DIR%"

REM Kill existing workers
taskkill /f /im python.exe 2>nul > nul
timeout /t 2 /nobreak > nul

REM Start new workers
set /a COUNT=1
:start_loop
if %COUNT% GTR %WORKERS_COUNT% goto :start_done
start /B python.exe "%PROJECT_DIR%\crypto_worker.py" "%COORDINATOR_URL%" > "%WORKER_DIR%\worker_%COUNT%.log" 2>&1
echo Worker %COUNT% iniciado...
set /a COUNT+=1
goto :start_loop

:start_done
timeout /t 3 /nobreak > nul

REM Count running workers
tasklist /fi "ImageName eq python.exe" 2>nul | findstr /c:"python.exe" > workers.tmp
set /a WORKERS_RUNNING=0
for /f "tokens=1" %%a in (workers.tmp) do set /a WORKERS_RUNNING+=1
del workers.tmp 2>nul

call :log_color "✅ Workers iniciados: %WORKERS_RUNNING% / %WORKERS_COUNT%" "GREEN"
goto :eof

:verify_installation
echo.
call :log_color "🔍 Verificando instalación..." "BLUE"

REM Check coordinator
curl -s --max-time 10 "%COORDINATOR_URL%/api/status" > nul 2>&1
if errorlevel 0 (
    curl -s "%COORDINATOR_URL%/api/status" | python -c "import sys,json; d=json.load(sys.stdin); print('Workers activos: '+str(d.get('workers',{}).get('active','0')))" 2>nul
    call :log_color "✅ Coordinator accesible" "GREEN"
) else (
    call :log_color "⚠️  Coordinator no accesible" "YELLOW"
)

REM Check local workers
tasklist /fi "ImageName eq python.exe" 2>nul | findstr /c:"python.exe" > nul
if errorlevel 0 (
    call :log_color "✅ Workers locales ejecutándose" "GREEN"
) else (
    call :log_color "⚠️  No hay workers ejecutándose" "YELLOW"
)
goto :eof

:print_summary
echo.
echo %GREEN%╔════════════════════════════════════════════════════════════════════════╗%NC%
echo %GREEN%║              þ INSTALACIîN COMPLETADA                                 ║%NC%
echo %GREEN%╚════════════════════════════════════════════════════════════════════════╝%NC%
echo.
echo %CYAN%RESUMEN:%NC%
echo.
echo    Sistema: %OS_NAME%
echo    CPUs disponibles: %CPU_CORES%
echo    Workers iniciados: %WORKERS_COUNT%
echo    Coordinator: %COORDINATOR_URL%
echo    Proyecto: %PROJECT_DIR%
echo    Logs: %WORKER_DIR%\worker_*.log
echo.
echo %CYAN%COMANDOS:%NC%
echo.
echo    Ver workers: tasklist /fi "ImageName eq python.exe"
echo    Ver logs: type %WORKER_DIR%\worker_1.log
echo    Reiniciar: %INSTALL_SCRIPT%
echo    Ver status: curl %COORDINATOR_URL%/api/status
echo.
goto :eof

REM ═══════════════════════════════════════════════════════════════════════════════
REM MAIN
REM ═══════════════════════════════════════════════════════════════════════════════
:main
echo.
echo %BLUE%╔════════════════════════════════════════════════════════════════════════╗%NC%
echo %BLUE%║     þ AUTO-INSTALLER WORKER - SISTEMA DE TRADING                  ║%NC%
echo %BLUE%║                                                                ║%NC%
echo %BLUE%║     Instalador autonomo para Windows                              ║%NC%
echo %BLUE%╚════════════════════════════════════════════════════════════════════════╝%NC%
echo.

REM Initialize log
mkdir "%WORKER_DIR%" 2>nul
echo # Install log - %date% %time% > "%LOG_FILE%"

REM Run installation
call :detect_os
call :detect_cpu_cores
call :setup_directories
call :install_dependencies
call :clone_or_update_project
call :create_startup_script
call :setup_auto_start
call :start_workers
call :verify_installation
call :print_summary

echo.
pause
endlocal
exit /b 0
