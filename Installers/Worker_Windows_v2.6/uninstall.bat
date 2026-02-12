@echo off
REM Bittrader Worker Uninstaller - Windows

setlocal

set INSTALL_DIR=%USERPROFILE%\.bittrader_worker

echo.
echo ================================================================
echo        Bittrader Worker Uninstaller (Windows)
echo ================================================================
echo.

echo This will completely remove the Bittrader Worker.
echo.
set /p CONFIRM="Are you sure? (y/N): "

if /i not "%CONFIRM%"=="y" (
    echo Uninstall cancelled.
    exit /b 0
)

echo.
echo Uninstalling...

REM Stop scheduled task
echo   * Stopping scheduled task...
schtasks /End /TN "BittraderWorker" >nul 2>&1
schtasks /Delete /TN "BittraderWorker" /F >nul 2>&1

REM Stop Ray
if exist "%INSTALL_DIR%\venv\Scripts\ray.exe" (
    echo   * Stopping Ray...
    "%INSTALL_DIR%\venv\Scripts\ray.exe" stop >nul 2>&1
)

REM Kill any running processes
taskkill /F /IM raylet.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

REM Remove firewall rule
echo   * Removing firewall rule...
netsh advfirewall firewall delete rule name="Bittrader Ray Worker" >nul 2>&1

REM Remove installation directory
if exist "%INSTALL_DIR%" (
    echo   * Removing installation directory...
    rmdir /S /Q "%INSTALL_DIR%"
)

echo.
echo OK Worker uninstalled successfully
echo.
echo Note: Python and system packages were not removed.
echo.

pause
