@echo off
title Ray Worker Setup (Windows)

echo ===================================================
echo      RAY WORKER SETUP FOR WINDOWS (PC GAMER)
echo ===================================================
echo.

REM 1. Check Python (Look for 3.9 specifically)
echo [1/3] Finding Python 3.9...

REM Try using the Windows Python Launcher "py" to find version 3.9
set PYTHON_CMD=python
py -3.9 --version >NUL 2>&1
if not errorlevel 1 (
    echo Found Python 3.9 via Launcher!
    set PYTHON_CMD=py -3.9
) else (
    echo Python Launcher '-3.9' not found. Checking default 'python'...
    python --version
)

REM 2. Create/Activate Environment
echo.
echo [2/3] Setting up Virtual Environment (worker_env)...
if not exist "worker_env" (
    echo Creating new venv with: %PYTHON_CMD%
    %PYTHON_CMD% -m venv worker_env
) else (
    echo Using existing venv...
)

echo Activating environment...
call worker_env\Scripts\activate.bat

echo.
echo Installing/Updating dependencies (Matching Mac versions)...
echo This may take a minute...
REM Install exact same libs as Mac
pip install "ray[default]" pandas numpy plotly python-dotenv coinbase-advanced-py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies. Check your internet connection.
    pause
    exit /b
)

echo.
echo [SUCCESS] Dependencies verified.
echo.

REM 3. Connect to Cluster
echo ===================================================
echo [3/3] CONNECT TO CLUSTER
echo ===================================================
echo.
echo Please look at your Mac (Head Node). 
echo It should say something like: "Found Head Node at: 10.0.0.XXX"
echo.

set /p HEAD_IP="Enter the IP of your Mac (Main): "

echo.
echo Connecting to Ray Cluster at %HEAD_IP%:6379...
echo (Keep this window open to keep the worker active)
echo.

set RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
ray start --address=%HEAD_IP%:6379 --block

pause
