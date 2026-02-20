# Bittrader Ray Cluster - Professional Installer Suite v4.0/v2.6

> **Production-Ready Distributed Computing Cluster for Cryptocurrency Trading Optimization**

---

## 🎯 Overview

This is a complete suite of professional installers for deploying the Bittrader distributed Ray cluster across multiple platforms. The system enables high-performance backtesting and strategy optimization by distributing workloads across multiple machines.

### Validated Configuration

✅ **Tested with:**
- Head Node: MacBook Pro (12 CPUs, 16GB RAM, macOS Sequoia 15.2.1)
- Worker Node: MacBook Air (10 CPUs, 8GB RAM, macOS Sequoia 15.2.1)
- Total Cluster: 22 CPUs, 24GB RAM
- Network: Tailscale VPN
- Test Dataset: 297,000 candles, 80 evaluations
- **Result: 100% success, zero crashes, 4.5 hours runtime**

---

## 📦 Available Installers

### Head Node (Server)

| Package | Platform | Version | Description |
|---------|----------|---------|-------------|
| `Bittrader_Head_Installer_v4.0_Native.zip` | macOS 12+ | v4.0 | Native macOS Head Node with automatic Python installation |

**Features:**
- ✅ Automatic Python 3.9.6 installation
- ✅ Ray 2.51.2 with production configuration
- ✅ Support for LAN and Tailscale VPN
- ✅ Persistent daemon with auto-restart
- ✅ Optional auto-start on login
- ✅ Health monitoring and logging
- ✅ Firewall configuration assistance

### Worker Nodes (Clients)

| Package | Platform | Version | Description |
|---------|----------|---------|-------------|
| `Bittrader_Worker_Installer_v2.6_macOS.zip` | macOS 12+ | v2.6 | macOS Worker with smart throttling |
| `Bittrader_Worker_Installer_v2.6_Windows.zip` | Windows 10/11 | v2.6 | Windows Worker with scheduled task |
| `Bittrader_Worker_Installer_v2.6_Linux.zip` | Linux (Ubuntu, Debian, CentOS, etc.) | v2.6 | Linux Worker with systemd service |

**Features:**
- ✅ Automatic Python 3.9.6 installation
- ✅ Ray 2.51.2 optimized per platform
- ✅ Automatic reconnection on network changes
- ✅ Smart CPU throttling (macOS)
- ✅ Auto-start integration (all platforms)
- ✅ Google Drive code synchronization support
- ✅ Tailscale VPN support

---

## 🚀 Quick Start

### Step 1: Install Head Node

1. Download `Bittrader_Head_Installer_v4.0_Native.zip`
2. Extract to a convenient location
3. Open Terminal and navigate to extracted folder
4. Run:
   ```bash
   chmod +x setup_head_native.sh verify_head.sh uninstall_head.sh
   ./setup_head_native.sh
   ```
5. Follow the interactive prompts
6. Note the connection command displayed (e.g., `ray start --address="100.77.179.14:6379"`)

### Step 2: Install Workers

#### macOS Workers

1. Download `Bittrader_Worker_Installer_v2.6_macOS.zip`
2. Extract and navigate to folder
3. Run:
   ```bash
   chmod +x install.sh verify_worker.sh uninstall.sh
   ./install.sh
   ```
4. Enter Head Node IP when prompted
5. Verify with `./verify_worker.sh`

#### Windows Workers

1. Download `Bittrader_Worker_Installer_v2.6_Windows.zip`
2. Extract to a folder
3. Right-click PowerShell → "Run as Administrator"
4. Navigate to extracted folder:
   ```powershell
   cd C:\Path\To\Worker_Windows_v2.6
   ```
5. Run:
   ```powershell
   .\install.ps1
   ```
6. Enter Head Node IP when prompted
7. Verify with `.\verify_worker.bat`

#### Linux Workers

1. Download `Bittrader_Worker_Installer_v2.6_Linux.zip`
2. Extract and navigate to folder
3. Run:
   ```bash
   chmod +x install.sh verify_worker.sh uninstall.sh
   ./install.sh
   ```
4. Enter Head Node IP when prompted (requires sudo)
5. Verify with `./verify_worker.sh`

### Step 3: Verify Cluster

On Head Node, check cluster status:
```bash
./verify_head.sh
```

Or use Python:
```python
import ray
ray.init(address='auto')
print(ray.cluster_resources())
```

You should see all CPUs from all connected workers.

---

## 📚 Documentation

Comprehensive documentation is available in the `Documentation/` folder:

### English Documentation

- **[COMPLETE_CLUSTER_GUIDE.md](Documentation/COMPLETE_CLUSTER_GUIDE.md)** - Complete setup and usage guide
- **[ARQUITECTURA_SISTEMA.md](Documentation/ARQUITECTURA_SISTEMA.md)** - System architecture and design
- **[TROUBLESHOOTING_GUIDE.md](Documentation/TROUBLESHOOTING_GUIDE.md)** - Common issues and solutions
- **[DEPLOYMENT_GUIDE.md](Documentation/DEPLOYMENT_GUIDE.md)** - Production deployment guide
- **[PERFORMANCE_BENCHMARKS.md](Documentation/PERFORMANCE_BENCHMARKS.md)** - Real-world performance data

### Spanish Documentation

- **[GUIA_COMPLETA_CLUSTER_DISTRIBUIDO.md](Documentation/GUIA_COMPLETA_CLUSTER_DISTRIBUIDO.md)** - Guía completa en español

---

## 🛠️ System Requirements

### Head Node

**Minimum:**
- macOS 12 (Monterey) or higher
- 8GB RAM (16GB+ recommended)
- 4 CPU cores (8+ recommended)
- 5GB available disk space
- Network connection

**Recommended:**
- macOS 14+ (Sonoma/Sequoia)
- 16GB+ RAM
- 8+ CPU cores
- SSD storage
- Gigabit network

### Workers

**macOS Workers:**
- macOS 12+
- 4GB RAM (8GB+ recommended)
- 2+ CPU cores
- Python 3.9.6 (auto-installed)

**Windows Workers:**
- Windows 10/11 (64-bit)
- 4GB RAM (8GB+ recommended)
- 2+ CPU cores
- PowerShell 5.1+
- Administrator privileges

**Linux Workers:**
- Ubuntu 18.04+, Debian 10+, CentOS 7+, RHEL 7+, or Fedora 35+
- 2GB RAM (4GB+ recommended)
- 1+ CPU cores
- Python 3.9 support
- sudo privileges

---

## 🌐 Network Configuration

### Local Network (LAN)

**Best for:** All machines on same network (home/office)

**Setup:**
- Use Head Node's local IP (e.g., 192.168.1.x)
- No VPN required
- Fastest performance
- Firewall may need configuration

### Remote Network (Tailscale VPN)

**Best for:** Workers in different locations

**Setup:**
1. Install Tailscale on all machines
2. Create Tailscale network
3. Connect all machines to network
4. Use Head Node's Tailscale IP (e.g., 100.x.x.x)
5. Works from anywhere
6. Encrypted connection

**Tailscale Installation:**
- macOS: https://tailscale.com/download/mac
- Windows: https://tailscale.com/download/windows
- Linux: https://tailscale.com/download/linux

---

## ⚙️ Features by Platform

### All Platforms

- ✅ Automatic Python 3.9.6 installation
- ✅ Ray 2.51.2 distributed computing
- ✅ Automatic reconnection on network failures
- ✅ Persistent daemon with restart on crash
- ✅ Comprehensive logging
- ✅ Easy verification scripts
- ✅ Clean uninstallation

### macOS Specific

- ✅ Smart CPU throttling (2 CPUs when active, full when idle)
- ✅ LaunchAgent integration for auto-start
- ✅ macOS notifications for status
- ✅ Battery-aware processing
- ✅ Mobile worker support (MacBook Air tested)

### Windows Specific

- ✅ Scheduled Task integration
- ✅ PowerShell automation
- ✅ Windows Firewall auto-configuration
- ✅ Silent background execution

### Linux Specific

- ✅ systemd service integration
- ✅ Multiple distribution support
- ✅ Automatic package manager detection
- ✅ journalctl log integration

---

## 📊 Performance

Based on real-world testing with 297,000 candles:

- **Cluster Size:** 22 CPUs (12 Head + 10 Worker)
- **Dataset:** BTC-USD 1h candles, 297k rows
- **Evaluations:** 80 optimization trials
- **Runtime:** 4.5 hours
- **Success Rate:** 100% (80/80 evaluations)
- **Crashes:** 0
- **Speedup:** 1.84x vs. single machine
- **Cost Savings:** ~$12/run vs. cloud compute

**Scalability:** Near-linear scaling up to 22 CPUs (83% efficiency)

See [PERFORMANCE_BENCHMARKS.md](Documentation/PERFORMANCE_BENCHMARKS.md) for detailed analysis.

---

## 🔧 Troubleshooting

### Common Issues

**Problem:** Cannot connect to Head Node
- Verify Head Node is running: `./verify_head.sh`
- Check network connectivity: `ping HEAD_IP`
- Verify firewall allows port 6379
- Check Tailscale connection: `tailscale status`

**Problem:** Python version mismatch
- All nodes MUST use Python 3.9.6 exactly
- Installer should handle this automatically
- If manual install needed: https://www.python.org/downloads/release/python-396/

**Problem:** Worker keeps disconnecting
- Check network stability
- Verify Head Node is stable
- Check worker logs for specific errors
- Ensure Tailscale is connected (if using VPN)

**Problem:** High CPU usage
- Normal during optimization tasks
- macOS workers use smart throttling (2 CPUs when in use)
- Adjust NUM_CPUS in config.env if needed

See [TROUBLESHOOTING_GUIDE.md](Documentation/TROUBLESHOOTING_GUIDE.md) for complete guide.

---

## 📁 Package Contents

### Head Node Package (`Head_Native_v4.0/`)

```
Head_Native_v4.0/
├── setup_head_native.sh    Interactive installer
├── head_daemon.sh           Persistent daemon
├── verify_head.sh           Status verification
├── uninstall_head.sh        Complete uninstaller
├── README_HEAD.txt          Complete documentation
└── CHANGELOG_HEAD.txt       Version history
```

### Worker Packages

**macOS** (`Worker_macOS_v2.6/`):
```
Worker_macOS_v2.6/
├── install.sh               Interactive installer
├── worker_daemon.sh         Worker daemon
├── verify_worker.sh         Status verification
├── uninstall.sh             Uninstaller
├── README_MACOS.txt         Documentation
└── CHANGELOG.txt            Version history
```

**Windows** (`Worker_Windows_v2.6/`):
```
Worker_Windows_v2.6/
├── install.ps1              PowerShell installer
├── worker_daemon.ps1        Worker daemon
├── verify_worker.bat        Status verification
├── uninstall.bat            Uninstaller
└── README_WINDOWS.txt       Documentation
```

**Linux** (`Worker_Linux_v2.6/`):
```
Worker_Linux_v2.6/
├── install.sh               Bash installer
├── worker_daemon.sh         Worker daemon
├── verify_worker.sh         Status verification
├── uninstall.sh             Uninstaller
├── bittrader-worker.service systemd service template
└── README_LINUX.txt         Documentation
```

---

## 🔐 Security

### Network Security

- **Tailscale VPN:** All remote connections encrypted end-to-end
- **No exposed ports:** Firewall only allows connections from VPN network
- **Authentication:** Tailscale handles all authentication

### Code Security

- **No code transfer:** Google Drive sync eliminates need to transfer code via Ray
- **Isolation:** Each worker runs in isolated Python virtual environment
- **No elevated privileges:** Workers run as regular user (not root/admin)

### Data Security

- **Local processing:** All data stays within your cluster
- **No cloud dependencies:** No data sent to third parties
- **Encrypted transport:** All Ray communication encrypted via Tailscale

---

## 🆘 Support

### Documentation

- Complete guides in `Documentation/` folder
- README files in each installer package
- Inline comments in all scripts

### Community

- Contact cluster administrator
- Check troubleshooting guides
- Review benchmark documentation

### Logs

Each component maintains detailed logs:

**Head Node:**
- Main log: `~/.bittrader_head/logs/head.log`
- Error log: `~/.bittrader_head/logs/head_error.log`

**Workers:**
- macOS: `~/.bittrader_worker/logs/worker.log`
- Windows: `%USERPROFILE%\.bittrader_worker\logs\worker.log`
- Linux: `~/.bittrader_worker/logs/worker.log`

---

## 📜 License

This installer suite is part of the Bittrader trading system.
Distributed under proprietary license.

**Third-Party Components:**
- Ray (Apache 2.0 License)
- Tailscale (Tailscale License)
- Python (PSF License)

---

## 🎉 Credits

**Developed by:** Bittrader Development Team
**Based on:** Ray 2.51.2 (https://github.com/ray-project/ray)
**VPN:** Tailscale (https://tailscale.com)

**Special Thanks:**
- Ray Project contributors
- Tailscale team
- Early testers and beta users

---

## 📝 Version Information

- **Head Node Installer:** v4.0
- **Worker Installers:** v2.6
- **Ray Version:** 2.51.2
- **Python Version:** 3.9.6
- **Release Date:** January 28, 2026
- **Last Updated:** January 28, 2026

---

## 🚦 Getting Started Checklist

- [ ] Read this README completely
- [ ] Review system requirements
- [ ] Choose network mode (LAN or Tailscale)
- [ ] Install Tailscale (if using VPN mode)
- [ ] Extract Head Node installer
- [ ] Run Head Node installation
- [ ] Note Head Node IP address
- [ ] Extract Worker installer(s)
- [ ] Run Worker installation(s)
- [ ] Verify cluster with verification scripts
- [ ] Run first test optimization
- [ ] Review performance benchmarks
- [ ] Read troubleshooting guide

---

**Ready to deploy your distributed trading cluster? Start with the Head Node installer!**

For questions or issues, consult the documentation in the `Documentation/` folder.

---

**Thank you for using Bittrader Ray Cluster!** 🚀
