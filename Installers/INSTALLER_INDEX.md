# Bittrader Ray Cluster - Installer Package Index

**Release Date:** January 28, 2026
**Cluster Version:** Head v4.0, Workers v2.6
**Ray Version:** 2.51.2
**Python Version:** 3.9.6

---

## 📦 Available Packages

### Head Node (Server)

| Package | Platform | Size | SHA256 Checksum |
|---------|----------|------|-----------------|
| `Bittrader_Head_Installer_v4.0_Native.zip` | macOS 12+ | 15 KB | `17c719cd460885e5643d9bfeaf0dc2749e7520698543a969f6a7ec97e336330c` |

**What's Included:**
- `setup_head_native.sh` - Interactive installer with automatic Python installation
- `head_daemon.sh` - Persistent daemon with health monitoring
- `verify_head.sh` - Comprehensive status verification
- `uninstall_head.sh` - Complete uninstaller
- `README_HEAD.txt` - Complete documentation (English/Spanish)
- `CHANGELOG_HEAD.txt` - Version history

**Requirements:**
- macOS 12 (Monterey) or higher
- 8GB RAM (16GB+ recommended)
- 4+ CPU cores (8+ recommended)
- Administrator privileges for Python installation

---

### Worker Nodes (Clients)

#### macOS Worker

| Package | Platform | Size | SHA256 Checksum |
|---------|----------|------|-----------------|
| `Bittrader_Worker_Installer_v2.6_macOS.zip` | macOS 12+ | 16 KB | `f9d1fc90a3ab524f982cd81f79ccecc708c6a038d959e6ccb3ddee12b3f62397` |

**What's Included:**
- `install.sh` - Interactive installer with Python auto-install
- `worker_daemon.sh` - Resilient worker daemon
- `verify_worker.sh` - Status verification
- `uninstall.sh` - Complete uninstaller
- `README_MACOS.txt` - Documentation (English/Spanish)
- `CHANGELOG.txt` - Version history

**Features:**
- ✅ Smart CPU throttling (2 CPUs active, full when idle)
- ✅ Mobile worker support (MacBook Air tested)
- ✅ LaunchAgent auto-start
- ✅ macOS notifications
- ✅ Battery-aware processing

**Requirements:**
- macOS 12+ (Monterey or higher)
- 4GB RAM (8GB+ recommended)
- 2+ CPU cores

---

#### Windows Worker

| Package | Platform | Size | SHA256 Checksum |
|---------|----------|------|-----------------|
| `Bittrader_Worker_Installer_v2.6_Windows.zip` | Windows 10/11 | 10 KB | `cbef0add5b2845885d2e6bf68c193f59819c54aadb11da61dcae4835ee64f46b` |

**What's Included:**
- `install.ps1` - PowerShell installer
- `worker_daemon.ps1` - Windows worker daemon
- `verify_worker.bat` - Status verification
- `uninstall.bat` - Complete uninstaller
- `README_WINDOWS.txt` - Complete documentation

**Features:**
- ✅ Scheduled Task integration
- ✅ Automatic firewall configuration
- ✅ Silent background execution
- ✅ PowerShell automation

**Requirements:**
- Windows 10 or Windows 11 (64-bit)
- PowerShell 5.1+
- 4GB RAM (8GB+ recommended)
- 2+ CPU cores
- Administrator privileges

---

#### Linux Worker

| Package | Platform | Size | SHA256 Checksum |
|---------|----------|------|-----------------|
| `Bittrader_Worker_Installer_v2.6_Linux.zip` | Ubuntu, Debian, CentOS, RHEL, Fedora | 10 KB | `4085b5ca2e612daa735680385be41e8040ce52e1b60ea78ec786a93c51d421e9` |

**What's Included:**
- `install.sh` - Distribution-agnostic installer
- `worker_daemon.sh` - Linux worker daemon
- `verify_worker.sh` - Status verification
- `uninstall.sh` - Complete uninstaller
- `bittrader-worker.service` - systemd service template
- `README_LINUX.txt` - Complete documentation

**Features:**
- ✅ systemd service integration
- ✅ Automatic package manager detection (apt, yum, dnf)
- ✅ Multi-distribution support
- ✅ journalctl log integration

**Requirements:**
- Ubuntu 18.04+, Debian 10+, CentOS 7+, RHEL 7+, or Fedora 35+
- 2GB RAM (4GB+ recommended)
- 1+ CPU cores
- sudo privileges

**Supported Distributions:**
- Ubuntu 18.04, 20.04, 22.04, 24.04
- Debian 10, 11, 12
- CentOS 7, 8, Stream
- RHEL 7, 8, 9
- Fedora 35+

---

## ✅ Checksum Verification

To verify package integrity after download:

### macOS/Linux:
```bash
shasum -a 256 Bittrader_Head_Installer_v4.0_Native.zip
# Compare output with checksum above
```

### Windows:
```powershell
Get-FileHash Bittrader_Worker_Installer_v2.6_Windows.zip -Algorithm SHA256
# Compare output with checksum above
```

### Verify All Packages:
```bash
shasum -a 256 -c SHA256SUMS.txt
```

---

## 📥 Installation Order

1. **Install Head Node first** (server)
   - Choose one machine to be the Head Node
   - Install using `Bittrader_Head_Installer_v4.0_Native.zip`
   - Note the connection IP displayed

2. **Install Workers** (clients)
   - Install on as many machines as you want to add to the cluster
   - Choose appropriate platform installer (macOS, Windows, or Linux)
   - Enter Head Node IP during installation

3. **Verify Cluster**
   - Run `verify_head.sh` on Head Node
   - Run `verify_worker.sh` on each Worker
   - Check total CPU count matches expected

---

## 🌐 Network Configuration

### Option 1: Local Network (LAN)

**When to use:** All machines on same network (home/office)

**Setup:**
- Use Head Node's local IP (e.g., 192.168.1.x)
- No VPN needed
- Fastest performance
- May need firewall configuration

**Pros:**
- ✅ Fastest performance
- ✅ No external dependencies
- ✅ Simple setup

**Cons:**
- ❌ Only works on same network
- ❌ May need firewall configuration

### Option 2: Tailscale VPN

**When to use:** Workers in different locations (home, office, cloud)

**Setup:**
1. Install Tailscale on all machines:
   - macOS: https://tailscale.com/download/mac
   - Windows: https://tailscale.com/download/windows
   - Linux: https://tailscale.com/download/linux

2. Connect all machines to same Tailscale network

3. Use Head Node's Tailscale IP (e.g., 100.x.x.x)

**Pros:**
- ✅ Works from anywhere
- ✅ Encrypted connection
- ✅ No firewall configuration needed
- ✅ Mobile workers supported

**Cons:**
- ❌ Requires internet
- ❌ Slight performance overhead (~5%)

---

## 📊 Tested Performance

**Test Configuration:**
- Head: MacBook Pro (12 CPUs)
- Worker: MacBook Air (10 CPUs)
- Network: Tailscale VPN
- Total: 22 CPUs

**Test Results:**
- Dataset: 297,000 candles
- Evaluations: 80
- Runtime: 4.5 hours
- Success Rate: 100%
- Crashes: 0
- Speedup: 1.84x vs. single machine

See [Documentation/PERFORMANCE_BENCHMARKS.md](../Documentation/PERFORMANCE_BENCHMARKS.md) for complete analysis.

---

## 📚 Documentation

Complete documentation available in `Documentation/` folder:

- **COMPLETE_CLUSTER_GUIDE.md** - Complete setup guide (English)
- **GUIA_COMPLETA_CLUSTER_DISTRIBUIDO.md** - Guía completa (Español)
- **ARQUITECTURA_SISTEMA.md** - System architecture
- **TROUBLESHOOTING_GUIDE.md** - Common issues and solutions
- **DEPLOYMENT_GUIDE.md** - Production deployment
- **PERFORMANCE_BENCHMARKS.md** - Performance analysis

---

## 🔄 Version History

### Head Node

- **v4.0** (January 28, 2026) - Initial production release
  - Native macOS Head Node
  - Automatic Python 3.9.6 installation
  - LAN and Tailscale support
  - Persistent daemon with auto-restart
  - Health monitoring

### Workers

- **v2.6** (January 28, 2026) - Multi-platform release
  - Improved network change detection
  - Enhanced Google Drive sync
  - Better Tailscale integration
  - Updated documentation
  - Windows and Linux installers added

- **v2.5** (January 2026)
  - Mobile worker mode
  - Automatic Python installation
  - Smart retry delays

- **v2.4** (December 2025)
  - Smart CPU throttling
  - Status notifications
  - Battery-aware processing

---

## 🆘 Support

### Quick Help

**Problem:** Cannot connect to Head Node
- Check Head Node is running: `./verify_head.sh`
- Test network: `ping HEAD_IP`
- Verify Tailscale: `tailscale status`

**Problem:** Python version mismatch
- All nodes must use Python 3.9.6 exactly
- Installer handles this automatically
- If needed, download from: https://www.python.org/downloads/release/python-396/

**Problem:** Worker disconnects frequently
- Check network stability
- Verify Head Node uptime
- Review worker logs
- Ensure Tailscale connected

### Full Documentation

See [Documentation/TROUBLESHOOTING_GUIDE.md](../Documentation/TROUBLESHOOTING_GUIDE.md)

---

## 📜 License

This installer suite is part of the Bittrader trading system.

**Third-Party Components:**
- Ray: Apache 2.0 License
- Tailscale: Tailscale License
- Python: PSF License

---

## 🎯 Next Steps

1. ✅ Download appropriate installer(s)
2. ✅ Verify checksums
3. ✅ Review documentation
4. ✅ Install Head Node
5. ✅ Install Worker(s)
6. ✅ Verify cluster
7. ✅ Run first optimization
8. ✅ Review benchmarks

---

**Package Generation Date:** January 28, 2026
**Generated By:** Bittrader Development Team
**Contact:** See cluster administrator

---

**Ready to deploy? Start with README_INSTALLERS.md in the parent directory!**
