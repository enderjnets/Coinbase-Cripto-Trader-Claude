@echo off
REM ============================================================================
REM CRYPTO WORKER INSTALLER - Windows
REM ============================================================================

echo ========================================
echo   CRYPTO WORKER INSTALLER - Windows
echo ========================================
echo.

set INSTALL_DIR=%USERPROFILE%\crypto_worker
set VENV_DIR=%USERPROFILE%\coinbase_worker_venv
set SCRIPT_DIR=%~dp0
set WORKER_FILES=%SCRIPT_DIR%..\worker_files

REM URL del coordinador predefinida
set COORDINATOR_URL=http://100.77.179.14:5001

echo URL del Coordinador: %COORDINATOR_URL%
echo.
echo Instalando worker...
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python no encontrado. Por favor instala Python 3.9+ desde python.org
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion
    pause
    exit /b 1
)

echo Python encontrado
python --version

REM Crear directorio de instalación
echo Creando directorio de instalacion...
if not exist "%INSTALL_DIR%\data" mkdir "%INSTALL_DIR%\data"

REM Copiar archivos
echo Copiando archivos...
copy "%WORKER_FILES%\*.py" "%INSTALL_DIR%\" >nul
copy "%WORKER_FILES%\data\*.csv" "%INSTALL_DIR%\data\" >nul

REM Crear entorno virtual
echo Creando entorno virtual...
python -m venv "%VENV_DIR%"

REM Instalar dependencias
echo Instalando dependencias...
call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip
pip install pandas pandas_ta requests ray python-dotenv

REM Crear script de ejecución
echo Creando script de ejecucion...
(
echo @echo off
echo set VENV_PATH=%VENV_DIR%
echo set COORDINATOR_URL=%COORDINATOR_URL%
echo set LOG_FILE=%%TEMP%%\worker_output.log
echo.
echo echo ========================================
echo echo CRYPTO WORKER - Windows
echo echo ========================================
echo echo Coordinator: %%COORDINATOR_URL%%
echo.
echo :loop
echo echo.
echo echo Iniciando worker...
echo cd /d "%INSTALL_DIR%"
echo call "%%VENV_PATH%%\Scripts\activate.bat"
echo set COORDINATOR_URL=%%COORDINATOR_URL%%
echo set PYTHONUNBUFFERED=1
echo python crypto_worker.py
echo echo Worker termino. Reiniciando en 5 segundos...
echo timeout /t 5 /nobreak
echo goto loop
) > "%INSTALL_DIR%\run_worker.bat"

echo.
echo ========================================
echo INSTALACION COMPLETADA
echo ========================================
echo.
echo Coordinador configurado: %COORDINATOR_URL%
echo.
echo Para iniciar el worker:
echo   cd %INSTALL_DIR%
echo   run_worker.bat
echo.
echo O haz doble clic en run_worker.bat
echo.
pause
