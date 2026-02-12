╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║         BITTRADER HEAD NODE INSTALLER v4.0 - NATIVE EDITION              ║
║                                                                          ║
║         Professional Ray Cluster Head Node for macOS                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TABLE OF CONTENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Overview
  2. System Requirements
  3. What's Included
  4. Quick Start Installation
  5. Manual Installation
  6. Configuration Options
  7. Verifying Installation
  8. Connecting Workers
  9. Troubleshooting
  10. Uninstallation
  11. Support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This installer configures your Mac as a Ray Head Node for the Bittrader
distributed computing cluster. The Head Node coordinates distributed tasks
across multiple Worker machines for high-performance backtesting and
optimization.

KEY FEATURES:
  ✓ Automatic Python 3.9.6 installation
  ✓ Ray 2.51.2 with production-ready configuration
  ✓ Support for local LAN and Tailscale VPN connections
  ✓ Persistent daemon with automatic restart on failure
  ✓ Optional auto-start on login
  ✓ Health monitoring and logging
  ✓ Firewall configuration assistance

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2. SYSTEM REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MINIMUM REQUIREMENTS:
  • macOS 12 (Monterey) or higher
  • 8GB RAM (16GB+ recommended)
  • 4 CPU cores (8+ recommended)
  • 5GB available disk space
  • Network connection (local or VPN)

OPTIONAL:
  • Tailscale (for remote worker connections)
  • Homebrew (for easier Tailscale installation)

VERIFIED CONFIGURATIONS:
  ✓ macOS Sequoia 15.2.1
  ✓ MacBook Pro (12 CPUs, 16GB RAM)
  ✓ Python 3.9.6
  ✓ Ray 2.51.2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  3. WHAT'S INCLUDED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILES IN THIS PACKAGE:

  setup_head_native.sh    Main installation script
  head_daemon.sh          Persistent Head Node daemon
  verify_head.sh          Status verification script
  uninstall_head.sh       Complete uninstaller
  README_HEAD.txt         This file (English/Spanish)
  CHANGELOG_HEAD.txt      Version history

INSTALLED COMPONENTS:

  ~/.bittrader_head/                    Installation directory
  ├── config.env                        Configuration file
  ├── head_daemon.sh                    Daemon script
  ├── head_daemon.lock                  Lock file (when running)
  └── logs/
      ├── head.log                      Main log file
      └── head_error.log                Error log file

  ~/Library/LaunchAgents/               Auto-start service
  └── com.bittrader.head.plist          LaunchAgent configuration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  4. QUICK START INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Extract this package to a convenient location

2. Open Terminal and navigate to the package directory:
   cd ~/Downloads/Bittrader_Head_Installer_v4.0_Native

3. Make the installer executable:
   chmod +x setup_head_native.sh verify_head.sh uninstall_head.sh

4. Run the installer:
   ./setup_head_native.sh

5. Follow the on-screen prompts to:
   • Choose network configuration (LAN or Tailscale)
   • Select Head Node IP address
   • Enable/disable auto-start
   • Configure firewall (if needed)

6. Verify installation:
   ./verify_head.sh

INSTALLATION TIME: Approximately 5-10 minutes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  5. MANUAL INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you prefer manual installation:

1. Install Python 3.9.6:
   Download from: https://www.python.org/ftp/python/3.9.6/
                  python-3.9.6-macos11.pkg

2. Install Ray 2.51.2:
   /usr/local/bin/python3.9 -m pip install --user ray[default]==2.51.2

3. Install dependencies:
   /usr/local/bin/python3.9 -m pip install --user numpy pandas python-dotenv

4. Create installation directory:
   mkdir -p ~/.bittrader_head/logs

5. Copy head_daemon.sh to ~/.bittrader_head/

6. Create config.env with your settings

7. Start the daemon:
   ~/.bittrader_head/head_daemon.sh &

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  6. CONFIGURATION OPTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NETWORK MODES:

  LOCAL LAN MODE:
    • Uses local network IP (e.g., 192.168.1.x)
    • Workers must be on same network
    • No VPN required
    • Best for: Home/office setups with workers nearby

  TAILSCALE VPN MODE:
    • Uses Tailscale IP (e.g., 100.x.x.x)
    • Workers can connect from anywhere
    • Requires Tailscale installation
    • Best for: Remote workers, multi-location deployments

CONFIGURATION FILE: ~/.bittrader_head/config.env

  HEAD_IP              IP address for Head Node
  LOCAL_IP             Local network IP
  TAILSCALE_IP         Tailscale VPN IP
  NUM_CPUS             Number of CPUs to allocate
  PYTHON_PATH          Path to Python 3.9.6
  RAY_PATH             Path to Ray binary
  INSTALL_DATE         Installation timestamp
  VERSION              Installer version

To change configuration:
  1. Stop the Head Node: ray stop
  2. Edit ~/.bittrader_head/config.env
  3. Restart: ~/.bittrader_head/head_daemon.sh &

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  7. VERIFYING INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run the verification script:
  ./verify_head.sh

This will check:
  ✓ Configuration settings
  ✓ Daemon status
  ✓ Ray Head process
  ✓ Cluster resources
  ✓ Network connectivity
  ✓ Port accessibility
  ✓ Recent logs

MANUAL VERIFICATION:

  Check if Ray is running:
    pgrep -f "ray.*head"

  View cluster status:
    python3.9 -c "import ray; ray.init(address='auto'); \
                  print(ray.cluster_resources())"

  Monitor logs:
    tail -f ~/.bittrader_head/logs/head.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  8. CONNECTING WORKERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After installing the Head Node, use the Worker Installer packages to add
worker machines to your cluster.

AVAILABLE WORKER INSTALLERS:
  • Bittrader_Worker_Installer_v2.6_macOS.zip
  • Bittrader_Worker_Installer_v2.6_Windows.zip
  • Bittrader_Worker_Installer_v2.6_Linux.zip

WORKER CONNECTION COMMAND:

  The installer will display a connection command like:
    ray start --address="100.77.179.14:6379"

  Use this command when installing workers.

NETWORK REQUIREMENTS:

  • Workers must be able to reach HEAD_IP:6379
  • If using Tailscale, workers must be on same network
  • If using LAN, workers must be on same local network
  • Firewall must allow incoming connections on port 6379

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  9. TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: Installation fails with Python errors
SOLUTION: Ensure Python 3.9.6 is installed correctly
          Run: /usr/local/bin/python3.9 --version
          Should output: Python 3.9.6

PROBLEM: Ray fails to start
SOLUTION: Check logs at ~/.bittrader_head/logs/head.log
          Try stopping existing instances: ray stop
          Verify port 6379 is not in use: lsof -i :6379

PROBLEM: Workers cannot connect
SOLUTION: Verify network connectivity: ping HEAD_IP
          Check firewall settings
          Ensure port 6379 is accessible: nc -z HEAD_IP 6379
          Verify Ray is running: pgrep -f "ray.*head"

PROBLEM: Tailscale IP changes after restart
SOLUTION: The daemon automatically detects IP changes
          Or manually update ~/.bittrader_head/config.env

PROBLEM: Daemon stops unexpectedly
SOLUTION: Check error log: ~/.bittrader_head/logs/head_error.log
          Verify auto-start is enabled:
            launchctl list | grep bittrader
          Restart manually: ~/.bittrader_head/head_daemon.sh &

PROBLEM: High CPU usage
SOLUTION: This is normal during optimization tasks
          To reduce CPU allocation, edit config.env
          Set NUM_CPUS to a lower value

For more help, see TROUBLESHOOTING_GUIDE.md in Documentation folder

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  10. UNINSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To completely remove the Head Node:

1. Run the uninstaller:
   ./uninstall_head.sh

2. Confirm when prompted

This will:
  • Stop the Head Node
  • Remove auto-start service
  • Delete installation directory
  • Clean up lock files

Note: Python 3.9.6 and Ray packages are NOT removed automatically.
To remove them manually:
  pip3.9 uninstall ray numpy pandas python-dotenv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  11. SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOCUMENTATION:
  • Complete Cluster Guide: Documentation/COMPLETE_CLUSTER_GUIDE.md
  • Architecture: Documentation/ARQUITECTURA_SISTEMA.md
  • Troubleshooting: Documentation/TROUBLESHOOTING_GUIDE.md
  • Deployment: Documentation/DEPLOYMENT_GUIDE.md

LOGS:
  • Main log: ~/.bittrader_head/logs/head.log
  • Error log: ~/.bittrader_head/logs/head_error.log

USEFUL COMMANDS:
  • Check status: ./verify_head.sh
  • View logs: tail -f ~/.bittrader_head/logs/head.log
  • Stop Head: ray stop
  • Start Head: ~/.bittrader_head/head_daemon.sh &
  • Restart Head: ray stop && ~/.bittrader_head/head_daemon.sh &

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ESPAÑOL - INSTALADOR HEAD NODE v4.0

Este instalador configura tu Mac como nodo principal (Head Node) para el
cluster distribuido de Bittrader.

INICIO RÁPIDO:
  1. chmod +x setup_head_native.sh verify_head.sh uninstall_head.sh
  2. ./setup_head_native.sh
  3. Sigue las instrucciones en pantalla
  4. ./verify_head.sh para verificar

REQUISITOS:
  • macOS 12+ (Monterey o superior)
  • 8GB RAM (16GB+ recomendado)
  • Python 3.9.6 (instalación automática)
  • Tailscale (opcional, para workers remotos)

DESINSTALACIÓN:
  ./uninstall_head.sh

Para más información consulta GUIA_COMPLETA_CLUSTER_DISTRIBUIDO.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Version: 4.0
Release Date: January 2026
Tested with: Ray 2.51.2, Python 3.9.6, macOS Sequoia 15.2.1

Thank you for using Bittrader!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
