╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║         BITTRADER WORKER INSTALLER v2.6 - LINUX EDITION                  ║
║                                                                          ║
║         Professional Ray Worker for Linux                               ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This installer configures your Linux machine as a Ray Worker in the Bittrader
distributed computing cluster. Workers contribute computing power for
high-performance backtesting and optimization.

SUPPORTED DISTRIBUTIONS:
  ✓ Ubuntu 18.04, 20.04, 22.04, 24.04
  ✓ Debian 10, 11, 12
  ✓ CentOS 7, 8, Stream
  ✓ RHEL 7, 8, 9
  ✓ Fedora 35+
  ✓ Other distributions with Python 3.9 support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SYSTEM REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MINIMUM:
  • Linux kernel 3.10+ (4.x+ recommended)
  • 2GB RAM (4GB+ recommended)
  • 1+ CPU cores (2+ recommended)
  • Network connection to Head Node
  • sudo privileges for installation

OPTIONAL:
  • Tailscale VPN (for remote Head Node)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  QUICK START
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Make scripts executable:
   chmod +x install.sh verify_worker.sh uninstall.sh

2. Run installer:
   ./install.sh

3. Follow prompts:
   • Enter Head Node IP
   • Choose auto-start option

4. Verify installation:
   ./verify_worker.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✓ Automatic Python 3.9 installation
  ✓ Ray 2.51.2 configured for Linux
  ✓ Persistent daemon with auto-reconnection
  ✓ Systemd service integration
  ✓ Automatic package manager detection
  ✓ Comprehensive logging
  ✓ Tailscale VPN support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The installer automatically:
  1. Detects your Linux distribution
  2. Installs Python 3.9 (if needed)
  3. Creates virtual environment
  4. Installs Ray 2.51.2 and dependencies
  5. Configures worker daemon
  6. Creates systemd service (optional)
  7. Starts worker

MANUAL INSTALLATION:

If you prefer manual setup:

1. Install Python 3.9:
   Ubuntu/Debian:
     sudo apt-get install python3.9 python3.9-venv python3.9-dev

   CentOS/RHEL/Fedora:
     sudo yum install python39 python39-devel

2. Create virtual environment:
   python3.9 -m venv ~/.bittrader_worker/venv

3. Install Ray:
   ~/.bittrader_worker/venv/bin/pip install ray[default]==2.51.2

4. Copy worker_daemon.sh to ~/.bittrader_worker/

5. Create config.env with HEAD_IP

6. Start daemon:
   ~/.bittrader_worker/worker_daemon.sh &

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SYSTEMD SERVICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you enabled auto-start, the worker runs as a systemd service.

USEFUL COMMANDS:

  Start worker:
    sudo systemctl start bittrader-worker

  Stop worker:
    sudo systemctl stop bittrader-worker

  Restart worker:
    sudo systemctl restart bittrader-worker

  Check status:
    sudo systemctl status bittrader-worker

  View logs:
    sudo journalctl -u bittrader-worker -f

  Enable auto-start:
    sudo systemctl enable bittrader-worker

  Disable auto-start:
    sudo systemctl disable bittrader-worker

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run verification script:
  ./verify_worker.sh

Checks:
  ✓ Installation directory
  ✓ Python version
  ✓ Ray installation
  ✓ Configuration
  ✓ Worker status

MANUAL VERIFICATION:

Check if Ray is running:
  pgrep -x raylet

View logs:
  tail -f ~/.bittrader_worker/logs/worker.log

Check network to Head Node:
  ping HEAD_IP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Problem: Cannot connect to Head Node
Solution:
  • Verify Head Node is running
  • Check network: ping HEAD_IP
  • Check logs: tail -f ~/.bittrader_worker/logs/worker.log
  • If using Tailscale: sudo tailscale status

Problem: Python 3.9 not available
Solution:
  Ubuntu/Debian:
    sudo add-apt-repository ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install python3.9 python3.9-venv python3.9-dev

  CentOS/RHEL:
    sudo yum install python39

Problem: Permission denied errors
Solution:
  • Ensure you have sudo privileges
  • Check file permissions: ls -la ~/.bittrader_worker
  • Service needs sudo: sudo systemctl status bittrader-worker

Problem: Service fails to start
Solution:
  • Check status: sudo systemctl status bittrader-worker
  • View logs: sudo journalctl -u bittrader-worker -n 50
  • Verify config: cat ~/.bittrader_worker/config.env
  • Test manually: ~/.bittrader_worker/worker_daemon.sh

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  UNINSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To remove the worker:
  ./uninstall.sh

This removes:
  • Installation directory
  • Systemd service
  • Lock files

Note: Python and system packages are NOT removed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LOGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Worker log:
  ~/.bittrader_worker/logs/worker.log

Service log (if using systemd):
  sudo journalctl -u bittrader-worker -f

Monitor worker log:
  tail -f ~/.bittrader_worker/logs/worker.log

Last 50 lines:
  tail -50 ~/.bittrader_worker/logs/worker.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NETWORK CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOCAL NETWORK:
  • Use Head Node's local IP
  • Both machines on same network
  • No VPN required

REMOTE (TAILSCALE):
  • Install Tailscale: https://tailscale.com/download/linux
  • Connect: sudo tailscale up
  • Use Head Node's Tailscale IP (100.x.x.x)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOCUMENTATION:
  • Complete Guide: Documentation/COMPLETE_CLUSTER_GUIDE.md
  • Troubleshooting: Documentation/TROUBLESHOOTING_GUIDE.md

CONTACT:
  Contact cluster administrator for support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Version: 2.6
Release Date: January 2026
Tested with: Ray 2.51.2, Python 3.9, Ubuntu 22.04, Debian 12

Thank you for contributing to the Bittrader cluster!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
