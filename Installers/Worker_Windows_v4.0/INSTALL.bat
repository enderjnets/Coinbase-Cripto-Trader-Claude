@echo off
echo ══════════════════════════════════════════════════════════════════
echo   BITTRADER WORKER v4.0 - WINDOWS INSTALLER
echo ══════════════════════════════════════════════════════════════════
echo.
echo This will install the Bittrader Worker on your system.
echo.
echo Press any key to continue or close this window to cancel...
pause > nul

powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"

pause
