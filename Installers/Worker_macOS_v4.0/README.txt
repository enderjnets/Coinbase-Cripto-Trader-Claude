╔═══════════════════════════════════════════════════════════════════════════════╗
║                    BITTRADER WORKER v4.0 - macOS                              ║
║                                                                               ║
║              Distributed Crypto Strategy Mining System                        ║
║                  4000x speedup with Numba JIT                                 ║
║                  Auto Sleep Prevention                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

INSTALLATION (FULLY AUTOMATIC!)
===============================

1. Extract this folder anywhere on your Mac

2. Open Terminal and navigate to the folder:
   cd Worker_macOS_v4.0

3. Run the installer:
   chmod +x install.sh && ./install.sh

4. Done! Workers start automatically.


FEATURES
========
- Pre-configured coordinator URL (no setup needed)
- Numba JIT acceleration (4000x speedup)
- Auto-detects CPU cores and configures optimal workers
- Auto-start on login
- SLEEP PREVENTION: System stays awake while workers run


COMMANDS
========
Location: ~/crypto_worker/

./start.sh   - Start workers (also prevents sleep)
./stop.sh    - Stop workers (restores sleep settings)
./status.sh  - Check worker status

Logs: tail -f /tmp/worker_1.log


SLEEP PREVENTION
================
When workers are running:
- Uses 'caffeinate' to prevent system sleep
- Your Mac will stay awake until you run ./stop.sh
- Sleep settings are automatically restored when stopping


REQUIREMENTS
============
- macOS 11+ (Big Sur or newer)
- Works with Intel and Apple Silicon Macs
- 4GB RAM minimum
- Internet connection


UNINSTALL
=========
1. Stop workers: ~/crypto_worker/stop.sh
2. Remove autostart:
   launchctl unload ~/Library/LaunchAgents/com.bittrader.worker.plist
3. Delete folder: rm -rf ~/crypto_worker


Version: 4.0
Build: February 2026
