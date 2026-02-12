╔═══════════════════════════════════════════════════════════════════════════════╗
║                    BITTRADER WORKER v4.0 - LINUX                              ║
║                                                                               ║
║              Distributed Crypto Strategy Mining System                        ║
║                  4000x speedup with Numba JIT                                 ║
║                  Auto Sleep Prevention                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

INSTALLATION (FULLY AUTOMATIC!)
===============================

1. Extract this folder anywhere

2. Open terminal and run:
   cd Worker_Linux_v4.0
   chmod +x install.sh && ./install.sh

3. Done! Workers start automatically.


FEATURES
========
- Pre-configured coordinator URL (no setup needed)
- Numba JIT acceleration (4000x speedup)
- Auto-detects CPU cores and configures optimal workers
- Auto-start on boot (via crontab)
- SLEEP PREVENTION: System stays awake while workers run


COMMANDS
========
Location: ~/crypto_worker/

./start.sh   - Start workers (also prevents sleep)
./stop.sh    - Stop workers (restores sleep settings)
./status.sh  - Check worker status

Logs: tail -f ~/crypto_worker/worker_1.log


SLEEP PREVENTION
================
When workers are running:
- Uses systemd-inhibit (if available) to prevent sleep
- Falls back to gsettings or xset for other desktop environments
- Your system will stay awake until you run ./stop.sh
- Sleep settings are automatically restored when stopping


SUPPORTED DISTROS
=================
- Ubuntu 20.04+
- Debian 11+
- Fedora 35+
- Arch Linux
- Linux Mint
- Any distro with Python 3.10+


REQUIREMENTS
============
- Linux with systemd (most modern distros)
- Python 3.10 or newer
- 4GB RAM minimum
- Internet connection


UNINSTALL
=========
1. Stop workers: ~/crypto_worker/stop.sh
2. Remove autostart: crontab -e (remove the @reboot line)
3. Delete folder: rm -rf ~/crypto_worker


Version: 4.0
Build: February 2026
