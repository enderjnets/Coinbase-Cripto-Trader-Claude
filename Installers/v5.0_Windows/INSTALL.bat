@echo off
REM ============================================================================
REM Bittrader Worker Installer v5.0 - Windows
REM Fecha: 2026-02-24
REM Cambios: Soporte multi-maquina, Numba JIT, Dashboard mejorado
REM ============================================================================

echo ==========================================
echo   Bittrader Worker Installer v5.0 - Windows
echo ==========================================
echo.

set COORDINATOR_URL=http://100.77.179.14:5001
set NUM_WORKERS=4
set WORK_DIR=%USERPROFILE%\crypto_worker

echo Coordinator: %COORDINATOR_URL%
echo Workers: %NUM_WORKERS%
echo Directory: %WORK_DIR%
echo.

REM Crear directorio
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"

REM Copiar archivos
echo Copiando archivos...
copy /Y "%~dp0crypto_worker.py" .
copy /Y "%~dp0strategy_miner.py" .
copy /Y "%~dp0numba_backtester.py" .
copy /Y "%~dp0backtester.py" .
copy /Y "%~dp0dynamic_strategy.py" .

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python no encontrado. Por favor instala Python 3.9+ desde https://www.python.org/downloads/
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

REM Crear entorno virtual
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Instalar dependencias
echo Instalando dependencias...
pip install --upgrade pip
pip install requests numpy numba pandas

REM Verificar Numba
echo Verificando Numba JIT...
python -c "import numba; print(f'Numba version: {numba.__version__}')"

REM Crear script de inicio
echo Creando scripts de inicio...
(
echo @echo off
echo cd /d "%WORK_DIR%"
echo call venv\Scripts\activate.bat
echo set COORDINATOR_URL=%COORDINATOR_URL%
echo set NUM_WORKERS=%NUM_WORKERS%
echo set USE_RAY=false
echo set PYTHONUNBUFFERED=1
echo.
echo for /L %%%%i in (1,1,%NUM_WORKERS%) do (
echo     start /B cmd /c "set WORKER_INSTANCE=%%%%i ^& python -u crypto_worker.py ^> worker_%%%%i.log 2^>^&1"
echo     echo Worker %%%%i iniciado
echo     timeout /t 2 ^>nul
echo )
echo echo %NUM_WORKERS% workers iniciados
) > start_workers.bat

REM Crear script de parada
(
echo @echo off
echo taskkill /F /IM python.exe /FI "WINDOWTITLE eq crypto_worker*" 2^>nul
echo taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq worker*" 2^>nul
echo echo Workers detenidos
) > stop_workers.bat

echo.
echo ==========================================
echo   Instalacion completada!
echo ==========================================
echo.
echo Para iniciar workers:
echo   cd %WORK_DIR%
echo   start_workers.bat
echo.
echo Para detener workers:
echo   cd %WORK_DIR%
echo   stop_workers.bat
echo.
pause
