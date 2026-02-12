╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║         BITTRADER WORKER INSTALLER v2.6 - WINDOWS EDITION                ║
║                                                                          ║
║         Professional Ray Worker for Windows 10/11                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This installer configures your Windows PC as a Ray Worker node in the
Bittrader distributed computing cluster. Workers contribute computing power
for high-performance backtesting and optimization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SYSTEM REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MINIMUM:
  • Windows 10 or Windows 11 (64-bit)
  • 4GB RAM (8GB+ recommended)
  • 2+ CPU cores (4+ recommended)
  • Network connection to Head Node
  • PowerShell 5.1 or higher
  • Administrator privileges

OPTIONAL:
  • Tailscale VPN (for remote Head Node connection)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INSTALLATION STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1: EXTRACT THE PACKAGE
  • Extract all files to a convenient location
  • Example: C:\Users\YourName\Downloads\Worker_Windows_v2.6

STEP 2: OPEN POWERSHELL AS ADMINISTRATOR
  • Click Start menu
  • Type "PowerShell"
  • Right-click "Windows PowerShell"
  • Select "Run as Administrator"

STEP 3: NAVIGATE TO PACKAGE DIRECTORY
  • In PowerShell, type:
    cd C:\Users\YourName\Downloads\Worker_Windows_v2.6
    (adjust path as needed)

STEP 4: ENABLE SCRIPT EXECUTION (IF NEEDED)
  • Run this command once:
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

STEP 5: RUN THE INSTALLER
  • Execute:
    .\install.ps1

STEP 6: FOLLOW PROMPTS
  • Enter Head Node IP when asked
  • Choose whether to enable auto-start
  • Wait for installation to complete

STEP 7: VERIFY INSTALLATION
  • Run:
    .\verify_worker.bat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✓ Automatic Python 3.9.6 installation
  ✓ Ray 2.51.2 configured for Windows
  ✓ Persistent daemon with auto-reconnection
  ✓ Auto-start on login (Scheduled Task)
  ✓ Automatic firewall configuration
  ✓ Comprehensive logging
  ✓ Tailscale VPN support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INSTALLED COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTALLATION DIRECTORY: %USERPROFILE%\.bittrader_worker

  .bittrader_worker\
  ├── config.env                Configuration file
  ├── venv\                     Python virtual environment
  ├── worker_daemon.ps1         Worker daemon script
  ├── worker_daemon.lock        Lock file (when running)
  └── logs\
      └── worker.log            Main log file

SCHEDULED TASK:
  Name: BittraderWorker
  Trigger: At user login
  Action: Start worker daemon in background

FIREWALL RULE:
  Name: Bittrader Ray Worker
  Direction: Inbound
  Program: Python (in venv)
  Action: Allow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run the verification script:
  .\verify_worker.bat

This checks:
  ✓ Installation directory
  ✓ Python version
  ✓ Ray installation
  ✓ Configuration
  ✓ Worker status

MANUAL VERIFICATION:

Check if Ray is running:
  tasklist | findstr raylet

View worker logs:
  type %USERPROFILE%\.bittrader_worker\logs\worker.log

Check scheduled task:
  schtasks /Query /TN "BittraderWorker"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEM: "Execution Policy" error when running install.ps1
SOLUTION:
  Run as Administrator:
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

PROBLEM: Cannot connect to Head Node
SOLUTION:
  • Verify Head Node is running
  • Check network: ping HEAD_IP
  • If using Tailscale, ensure it's connected
  • Check firewall settings
  • View logs: type %USERPROFILE%\.bittrader_worker\logs\worker.log

PROBLEM: Python installation fails
SOLUTION:
  Download manually from:
  https://www.python.org/ftp/python/3.9.6/python-3.9.6-amd64.exe
  Install, then run install.ps1 again

PROBLEM: Worker doesn't start automatically
SOLUTION:
  Check scheduled task:
    schtasks /Query /TN "BittraderWorker"
  Enable manually:
    schtasks /Run /TN "BittraderWorker"

PROBLEM: High CPU usage
SOLUTION:
  • Normal during optimization tasks
  • Adjust CPU allocation in config.env
  • Check Task Manager for CPU usage by Python

PROBLEM: Firewall blocking connections
SOLUTION:
  Manually add firewall rule:
    Control Panel > Windows Defender Firewall > Allow an app
    Add: %USERPROFILE%\.bittrader_worker\venv\Scripts\python.exe

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  UNINSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To remove the worker:
  .\uninstall.bat

This removes:
  • Installation directory
  • Scheduled task
  • Firewall rule
  • Lock files

Note: Python 3.9.6 is NOT removed (may be used by other programs)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ADVANCED USAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MANUAL START:
  PowerShell -File "%USERPROFILE%\.bittrader_worker\worker_daemon.ps1"

MANUAL STOP:
  %USERPROFILE%\.bittrader_worker\venv\Scripts\ray.exe stop

VIEW LOGS IN REAL-TIME:
  Get-Content "%USERPROFILE%\.bittrader_worker\logs\worker.log" -Wait

RECONFIGURE HEAD NODE IP:
  1. Stop worker: ray.exe stop
  2. Edit: %USERPROFILE%\.bittrader_worker\config.env
  3. Change HEAD_IP value
  4. Restart worker

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NETWORK CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOCAL NETWORK (LAN):
  • Use Head Node's local IP (e.g., 192.168.1.x)
  • Both machines must be on same network
  • No VPN required
  • Fastest performance

REMOTE CONNECTION (TAILSCALE):
  • Install Tailscale: https://tailscale.com/download/windows
  • Connect to Tailscale network
  • Use Head Node's Tailscale IP (e.g., 100.x.x.x)
  • Works from anywhere
  • Encrypted connection

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LOGS AND MONITORING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAIN LOG:
  %USERPROFILE%\.bittrader_worker\logs\worker.log

View recent logs:
  type %USERPROFILE%\.bittrader_worker\logs\worker.log

Monitor in real-time (PowerShell):
  Get-Content %USERPROFILE%\.bittrader_worker\logs\worker.log -Wait

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SUPPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOCUMENTATION:
  • Complete Guide: Documentation\COMPLETE_CLUSTER_GUIDE.md
  • Architecture: Documentation\ARQUITECTURA_SISTEMA.md
  • Troubleshooting: Documentation\TROUBLESHOOTING_GUIDE.md

CONTACT:
  Contact cluster administrator for support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Version: 2.6
Release Date: January 2026
Tested with: Ray 2.51.2, Python 3.9.6, Windows 10/11

Thank you for contributing to the Bittrader cluster!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
