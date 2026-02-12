#!/bin/bash
#
# Bittrader Worker Installer v2.6 - Linux Edition
# Professional installer for Ray Worker on Linux
# Supports Ubuntu, Debian, CentOS, Fedora, and other major distributions
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_worker"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║    BITTRADER WORKER INSTALLER v2.6 - LINUX EDITION           ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║    Professional Ray Worker for Linux                        ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 1. DETECT LINUX DISTRIBUTION
# ============================================================
echo -e "${YELLOW}[1/8]${NC} Detecting Linux distribution..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
    OS_VERSION=$VERSION_ID
    echo -e "   ✅ $OS_NAME $OS_VERSION"
else
    OS_NAME="Unknown"
    echo -e "${YELLOW}   ⚠️  Could not detect distribution${NC}"
fi

# Detect package manager
if command -v apt-get &> /dev/null; then
    PKG_MGR="apt-get"
    PKG_UPDATE="sudo apt-get update -qq"
    PKG_INSTALL="sudo apt-get install -y"
elif command -v yum &> /dev/null; then
    PKG_MGR="yum"
    PKG_UPDATE="sudo yum check-update || true"
    PKG_INSTALL="sudo yum install -y"
elif command -v dnf &> /dev/null; then
    PKG_MGR="dnf"
    PKG_UPDATE="sudo dnf check-update || true"
    PKG_INSTALL="sudo dnf install -y"
else
    echo -e "${RED}❌ No supported package manager found${NC}"
    echo "   Supported: apt-get, yum, dnf"
    exit 1
fi

echo -e "   ✅ Package manager: $PKG_MGR"

# ============================================================
# 2. CHECK/INSTALL PYTHON 3.9
# ============================================================
echo ""
echo -e "${YELLOW}[2/8]${NC} Checking Python 3.9..."

PYTHON_CMD=""

# Check for Python 3.9
for candidate in python3.9 python3 python; do
    if command -v $candidate &> /dev/null; then
        VERSION=$($candidate --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        MAJOR=$(echo $VERSION | cut -d. -f1)
        MINOR=$(echo $VERSION | cut -d. -f2)

        if [ "$MAJOR" == "3" ] && [ "$MINOR" == "9" ]; then
            PYTHON_CMD=$candidate
            echo -e "   ✅ Found Python $VERSION ($candidate)"
            break
        fi
    fi
done

# Install Python 3.9 if not found
if [ -z "$PYTHON_CMD" ]; then
    echo -e "   Python 3.9 not found. Installing..."

    $PKG_UPDATE

    if [ "$PKG_MGR" == "apt-get" ]; then
        # Ubuntu/Debian
        $PKG_INSTALL software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
        $PKG_UPDATE
        $PKG_INSTALL python3.9 python3.9-venv python3.9-dev
        PYTHON_CMD="python3.9"
    elif [ "$PKG_MGR" == "yum" ] || [ "$PKG_MGR" == "dnf" ]; then
        # CentOS/RHEL/Fedora
        $PKG_INSTALL python39 python39-devel
        PYTHON_CMD="python3.9"
    fi

    if command -v $PYTHON_CMD &> /dev/null; then
        echo -e "   ✅ Python 3.9 installed successfully"
    else
        echo -e "${RED}❌ Failed to install Python 3.9${NC}"
        echo "   Install manually and run this script again"
        exit 1
    fi
fi

# Install pip if needed
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "   Installing pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON_CMD
fi

echo -e "   ✅ Using Python: $PYTHON_CMD"

# ============================================================
# 3. GET HEAD NODE IP
# ============================================================
echo ""
echo -e "${YELLOW}[3/8]${NC} Configuring cluster connection..."

HEAD_IP=""
CONFIG_FILE="$INSTALL_DIR/config.env"

# Check for existing configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo -e "   Existing configuration found"
    echo -e "   Head Node IP: $HEAD_IP"
    read -p "   Keep this configuration? (Y/n): " KEEP_CONFIG
    if [[ "$KEEP_CONFIG" =~ ^[Nn]$ ]]; then
        HEAD_IP=""
    fi
fi

if [ -z "$HEAD_IP" ]; then
    echo ""
    echo -e "   Enter the Head Node IP address (provided by administrator)"
    echo -e "   • For local network: use local IP (e.g., 192.168.1.x)"
    echo -e "   • For remote: use Tailscale IP (e.g., 100.x.x.x)"
    echo ""
    read -p "   Head Node IP: " HEAD_IP

    if [ -z "$HEAD_IP" ]; then
        echo -e "${RED}❌ Head Node IP is required${NC}"
        exit 1
    fi
fi

echo -e "   ✅ Head Node: $HEAD_IP"

# ============================================================
# 4. CHECK NETWORK CONNECTIVITY
# ============================================================
echo ""
echo -e "${YELLOW}[4/8]${NC} Checking network connectivity..."

if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
    echo -e "   ✅ Head Node reachable"
else
    echo -e "${YELLOW}   ⚠️  Head Node not reachable${NC}"
    echo -e "   This may be normal if:"
    echo -e "   • Head Node is not running yet"
    echo -e "   • Tailscale VPN not connected"
    echo -e "   • Firewall blocking ICMP"

    # Check for Tailscale
    if command -v tailscale &> /dev/null; then
        echo -e "   Tailscale found. Checking status..."
        if tailscale status &> /dev/null; then
            TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
            echo -e "   ✅ Tailscale connected: $TAILSCALE_IP"
        else
            echo -e "${YELLOW}   ⚠️  Tailscale not connected${NC}"
            echo -e "   Run: sudo tailscale up"
        fi
    else
        echo -e "   Tailscale not installed"
        echo -e "   For remote connections: https://tailscale.com/download/linux"
    fi
fi

# ============================================================
# 5. INSTALL DEPENDENCIES
# ============================================================
echo ""
echo -e "${YELLOW}[5/8]${NC} Installing system dependencies..."

# Install build dependencies for Ray
if [ "$PKG_MGR" == "apt-get" ]; then
    $PKG_INSTALL build-essential curl git
elif [ "$PKG_MGR" == "yum" ] || [ "$PKG_MGR" == "dnf" ]; then
    $PKG_INSTALL gcc gcc-c++ make curl git
fi

echo -e "   ✅ Dependencies installed"

# ============================================================
# 6. INSTALL RAY AND PYTHON PACKAGES
# ============================================================
echo ""
echo -e "${YELLOW}[6/8]${NC} Installing Ray and dependencies..."

# Create installation directory
mkdir -p "$INSTALL_DIR/logs"

# Create virtual environment
VENV_PATH="$INSTALL_DIR/venv"
echo -e "   Creating virtual environment..."
$PYTHON_CMD -m venv "$VENV_PATH"

VENV_PYTHON="$VENV_PATH/bin/python"
VENV_PIP="$VENV_PATH/bin/pip"

# Upgrade pip
echo -e "   Upgrading pip..."
$VENV_PIP install --upgrade pip setuptools wheel --quiet

# Install Ray
echo -e "   Installing Ray 2.51.2 (this may take several minutes)..."
$VENV_PIP install "ray==2.9.0==2.51.2" --quiet

# Install dependencies
echo -e "   Installing dependencies..."
$VENV_PIP install numpy pandas python-dotenv --quiet

# Verify installation
echo -e "   Verifying Ray installation..."
if $VENV_PYTHON -c "import ray; print(f'Ray {ray.__version__}')" &> /dev/null; then
    RAY_VERSION=$($VENV_PYTHON -c "import ray; print(ray.__version__)")
    echo -e "   ✅ Ray $RAY_VERSION installed successfully"
else
    echo -e "${RED}❌ Ray installation failed${NC}"
    exit 1
fi

RAY_PATH="$VENV_PATH/bin/ray"

# ============================================================
# 7. INSTALL WORKER DAEMON
# ============================================================
echo ""
echo -e "${YELLOW}[7/8]${NC} Installing worker daemon..."

# Copy daemon script
cp "$SCRIPT_DIR/worker_daemon.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/worker_daemon.sh"

# Detect CPU count
NUM_CPUS=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo)

# Save configuration
cat > "$CONFIG_FILE" << EOF
HEAD_IP=$HEAD_IP
NUM_CPUS=$NUM_CPUS
INSTALL_DATE=$(date)
VERSION=2.6
PYTHON_PATH=$VENV_PYTHON
RAY_PATH=$RAY_PATH
EOF

echo -e "   ✅ Daemon installed"
echo -e "   ✅ Configuration saved"

# ============================================================
# 8. CREATE SYSTEMD SERVICE
# ============================================================
echo ""
echo -e "${YELLOW}[8/8]${NC} Configuring auto-start service..."

read -p "   Enable auto-start on boot? (Y/n): " ENABLE_AUTOSTART

if [[ ! "$ENABLE_AUTOSTART" =~ ^[Nn]$ ]]; then
    # Create systemd service
    SERVICE_FILE="/etc/systemd/system/bittrader-worker.service"

    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Bittrader Ray Worker
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=$INSTALL_DIR/worker_daemon.sh
Restart=always
RestartSec=10
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1"
Environment="RAY_ENABLE_IPV6=0"

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable service
    sudo systemctl enable bittrader-worker.service

    echo -e "   ✅ Auto-start enabled (systemd service)"
    AUTO_START_ENABLED=true
else
    echo -e "   ⊘ Auto-start disabled"
    AUTO_START_ENABLED=false
fi

# ============================================================
# INSTALLATION COMPLETE
# ============================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║          ✅ INSTALLATION COMPLETED SUCCESSFULLY              ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                  WORKER CONFIGURATION                         ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   ${BLUE}Head Node IP:${NC}     $HEAD_IP"
echo -e "   ${BLUE}Port:${NC}             6379"
echo -e "   ${BLUE}CPUs Available:${NC}   $NUM_CPUS"
echo -e "   ${BLUE}Python:${NC}           $PYTHON_CMD"
echo -e "   ${BLUE}Ray Version:${NC}      $RAY_VERSION"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                      NEXT STEPS                               ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
if [ "$AUTO_START_ENABLED" == "true" ]; then
    echo -e "   1. Worker will start automatically on next boot"
    echo -e "   2. To start now: sudo systemctl start bittrader-worker"
else
    echo -e "   1. To start worker: $INSTALL_DIR/worker_daemon.sh &"
fi
echo -e "   3. To verify status: ./verify_worker.sh"
echo -e "   4. To uninstall: ./uninstall.sh"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                        LOGS                                   ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   Worker log:  $INSTALL_DIR/logs/worker.log"
if [ "$AUTO_START_ENABLED" == "true" ]; then
    echo -e "   Service log: sudo journalctl -u bittrader-worker -f"
fi
echo ""
echo -e "${GREEN}Thank you for joining the Bittrader cluster!${NC}"
echo ""

# Start now?
read -p "Start worker now? (Y/n): " START_NOW

if [[ ! "$START_NOW" =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${BLUE}Starting worker...${NC}"

    if [ "$AUTO_START_ENABLED" == "true" ]; then
        sudo systemctl start bittrader-worker
        sleep 3
        if sudo systemctl is-active --quiet bittrader-worker; then
            echo -e "   ${GREEN}✅ Worker service started${NC}"
        else
            echo -e "${YELLOW}   ⚠️  Service may still be starting...${NC}"
            echo -e "   Check: sudo systemctl status bittrader-worker"
        fi
    else
        nohup "$INSTALL_DIR/worker_daemon.sh" > /dev/null 2>&1 &
        sleep 3
        echo -e "   ${GREEN}✅ Worker started in background${NC}"
    fi

    echo ""
    echo -e "   Check status with: ./verify_worker.sh"
    echo ""
fi

echo -e "${BLUE}Installation directory: $INSTALL_DIR${NC}"
echo ""
