@echo off
REM Bittrader Worker Verification Script - Windows
REM Verifies Ray Worker installation and connection

setlocal enabledelayedexpansion

set INSTALL_DIR=%USERPROFILE%\.bittrader_worker

echo.
echo ================================================================
echo        Bittrader Worker Verification (Windows)
echo ================================================================
echo.

REM Check if installed
if not exist "%INSTALL_DIR%" (
    echo ERROR: Worker not installed
    echo Run install.ps1 to install
    exit /b 1
)

echo [1/5] Checking installation...
echo    OK Installation directory exists

REM Check Python
echo.
echo [2/5] Checking Python...

if exist "%INSTALL_DIR%\venv\Scripts\python.exe" (
    for /f "tokens=2" %%v in ('"%INSTALL_DIR%\venv\Scripts\python.exe" --version 2^>^&1') do set PYTHON_VERSION=%%v
    echo    OK Python version: !PYTHON_VERSION!
) else (
    echo    ERROR: Python not found in venv
    exit /b 1
)

REM Check Ray
echo.
echo [3/5] Checking Ray...

if exist "%INSTALL_DIR%\venv\Scripts\ray.exe" (
    echo    OK Ray executable found
) else (
    echo    ERROR: Ray not installed
    exit /b 1
)

REM Check configuration
echo.
echo [4/5] Checking configuration...

if exist "%INSTALL_DIR%\config.env" (
    echo    OK Configuration found
    for /f "tokens=1,2 delims==" %%a in (%INSTALL_DIR%\config.env) do (
        if "%%a"=="HEAD_IP" echo       Head Node IP: %%b
    )
) else (
    echo    ERROR: config.env not found
    exit /b 1
)

REM Check Ray status
echo.
echo [5/5] Checking Ray status...

tasklist /FI "IMAGENAME eq raylet.exe" 2>NUL | find /I /N "raylet.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo    OK Ray worker is running
) else (
    echo    WARNING: Ray worker not running
    echo    Start with: PowerShell -File "%INSTALL_DIR%\worker_daemon.ps1"
)

echo.
echo ================================================================
echo                        SUMMARY
echo ================================================================
echo.
echo Installation appears OK.
echo.
echo Logs: %INSTALL_DIR%\logs\worker.log
echo.
echo To monitor logs:
echo    type %INSTALL_DIR%\logs\worker.log
echo.

pause
