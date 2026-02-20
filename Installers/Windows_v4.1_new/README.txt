╔═══════════════════════════════════════════════════════════════════════════════╗
║                    BITTRADER WORKER v4.0 - WINDOWS                            ║
║                                                                               ║
║              Distributed Crypto Strategy Mining System                        ║
║                  4000x speedup with Numba JIT                                 ║
║                  Auto Sleep Prevention                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

INSTALLATION (SUPER EASY!)
==========================

1. Extract this folder anywhere

2. Double-click: INSTALL.bat

3. Done! Workers start automatically.


FEATURES
========
- Pre-configured coordinator URL (no setup needed)
- Numba JIT acceleration (4000x speedup)
- Auto-installs Python if needed
- Auto-detects CPU cores and configures optimal workers
- Auto-start when Windows boots
- SLEEP PREVENTION: PC stays awake while workers run


COMMANDS
========
Location: C:\Users\YourName\crypto_worker\

start.bat   - Start workers (also prevents sleep)
stop.bat    - Stop workers (restores sleep settings)
status.bat  - Check status


SLEEP PREVENTION
================
When workers are running:
- Uses powercfg to prevent system sleep/hibernate
- Your PC will stay awake until you run stop.bat
- Sleep settings are automatically restored when stopping
- Default restore: 30 min (AC) / 15 min (battery)


REQUIREMENTS
============
- Windows 10 or 11
- Internet connection
- 4GB RAM minimum


TROUBLESHOOTING
===============
1. If "Windows protected your PC" appears:
   Click "More info" then "Run anyway"

2. If PowerShell blocks the script:
   Right-click INSTALL.bat -> Run as Administrator

3. Check logs in: C:\Users\YourName\crypto_worker\worker_1.log


UNINSTALL
=========
1. Run stop.bat
2. Delete the shortcut from:
   C:\Users\YourName\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
3. Delete folder: C:\Users\YourName\crypto_worker


Version: 4.0
Build: February 2026
