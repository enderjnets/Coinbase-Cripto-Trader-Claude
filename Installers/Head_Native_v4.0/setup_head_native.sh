#!/bin/bash
#
# Bittrader Head Node Installer v4.0 - Native Edition
# Professional installer for Ray Head Node on macOS
# Supports both local LAN and Tailscale VPN connections
#
# Requirements:
# - macOS 12 (Monterey) or higher
# - Python 3.9.6
# - 8GB+ RAM recommended
# - Tailscale (optional, for remote workers)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_head"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║    🎯 BITTRADER HEAD NODE INSTALLER v4.0 - NATIVE EDITION   ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║    Professional Ray Cluster Head Node for macOS             ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}This installer will configure this Mac as the Ray Head Node.${NC}"
echo -e "${BLUE}Workers can connect from local network or remotely via Tailscale.${NC}"
echo ""

# ============================================================
# 1. CHECK MACOS VERSION
# ============================================================
echo -e "${YELLOW}[1/8]${NC} Checking system requirements..."

OS_VERSION=$(sw_vers -productVersion)
MAJOR_VERSION=$(echo $OS_VERSION | cut -d. -f1)

if [ "$MAJOR_VERSION" -lt 12 ]; then
    echo -e "${RED}❌ Error: macOS 12 (Monterey) or higher required.${NC}"
    echo "   Your version: $OS_VERSION"
    exit 1
fi
echo -e "   ✅ macOS $OS_VERSION compatible"

# Check RAM
TOTAL_RAM_GB=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
if [ "$TOTAL_RAM_GB" -lt 8 ]; then
    echo -e "${YELLOW}   ⚠️  Warning: Only ${TOTAL_RAM_GB}GB RAM detected. 8GB+ recommended.${NC}"
else
    echo -e "   ✅ RAM: ${TOTAL_RAM_GB}GB"
fi

# Detect CPUs
NUM_CPUS=$(sysctl -n hw.ncpu)
echo -e "   ✅ CPUs: $NUM_CPUS cores available"

# ============================================================
# 2. CHECK PYTHON 3.9.6
# ============================================================
echo ""
echo -e "${YELLOW}[2/8]${NC} Verifying Python 3.9.6..."

PYTHON_CMD=""
PYTHON_VERSION=""

# Check standard paths for Python 3.9.6 EXACTLY
for candidate in "/usr/local/bin/python3.9" "/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9" "/opt/homebrew/bin/python3.9" "/usr/bin/python3.9"; do
    if [ -f "$candidate" ]; then
        VERSION=$("$candidate" --version 2>&1 | cut -d' ' -f2)
        if [ "$VERSION" == "3.9.6" ]; then
            PYTHON_CMD="$candidate"
            PYTHON_VERSION="$VERSION"
            echo -e "   ✅ Found Python 3.9.6 at: $candidate"
            break
        fi
    fi
done

# If Python 3.9.6 not found, offer to install
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}   ⚠️  Python 3.9.6 not found.${NC}"
    echo ""
    read -p "   Install Python 3.9.6 automatically? (Y/n): " INSTALL_PYTHON

    if [[ ! "$INSTALL_PYTHON" =~ ^[Nn]$ ]]; then
        echo -e "   Downloading Python 3.9.6 (this may take 2-3 minutes)..."

        PYTHON_PKG="/tmp/python-3.9.6-macos11.pkg"

        if curl -L -o "$PYTHON_PKG" "https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg" 2>&1; then
            echo -e "   ✅ Download completed"

            echo -e "   Installing Python 3.9.6 (requires administrator password)..."

            if sudo installer -pkg "$PYTHON_PKG" -target / 2>&1; then
                echo -e "   ✅ Python 3.9.6 installed successfully"
                rm -f "$PYTHON_PKG"

                # Find newly installed Python
                if [ -f "/usr/local/bin/python3.9" ]; then
                    PYTHON_CMD="/usr/local/bin/python3.9"
                elif [ -f "/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9" ]; then
                    PYTHON_CMD="/Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9"
                fi

                PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | cut -d' ' -f2)
            else
                echo -e "${RED}   ❌ Failed to install Python 3.9.6${NC}"
                rm -f "$PYTHON_PKG"
                exit 1
            fi
        else
            echo -e "${RED}   ❌ Failed to download Python 3.9.6${NC}"
            echo -e "   Download manually from:"
            echo -e "   https://www.python.org/ftp/python/3.9.6/python-3.9.6-macos11.pkg"
            exit 1
        fi
    else
        echo -e "${RED}   ❌ Python 3.9.6 is required. Please install and run again.${NC}"
        exit 1
    fi
fi

echo -e "   ✅ Using Python: $PYTHON_CMD (v$PYTHON_VERSION)"

# ============================================================
# 3. DETECT NETWORK CONFIGURATION
# ============================================================
echo ""
echo -e "${YELLOW}[3/8]${NC} Detecting network configuration..."

# Get primary local IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")

if [ -n "$LOCAL_IP" ]; then
    echo -e "   ✅ Local IP: $LOCAL_IP"
else
    echo -e "${YELLOW}   ⚠️  No local network detected${NC}"
fi

# Check for Tailscale
TAILSCALE_IP=""
TAILSCALE_AVAILABLE=false

if command -v tailscale &> /dev/null || [ -f "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then
    TAILSCALE_AVAILABLE=true

    if command -v tailscale &> /dev/null; then
        TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
    else
        TAILSCALE_IP=$(/Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4 2>/dev/null || echo "")
    fi

    if [ -n "$TAILSCALE_IP" ]; then
        echo -e "   ✅ Tailscale IP: $TAILSCALE_IP"
    else
        echo -e "${YELLOW}   ⚠️  Tailscale installed but not connected${NC}"
    fi
else
    echo -e "   ℹ️  Tailscale not installed (optional, for remote workers)"
fi

# ============================================================
# 4. CHOOSE HEAD NODE IP
# ============================================================
echo ""
echo -e "${YELLOW}[4/8]${NC} Configuring Head Node IP address..."

echo ""
echo -e "   ${BLUE}Select which IP to use for the Head Node:${NC}"
echo ""

OPTIONS=()
if [ -n "$LOCAL_IP" ]; then
    echo -e "   1) Local Network: $LOCAL_IP"
    echo -e "      ${CYAN}→ Workers must be on same LAN${NC}"
    OPTIONS+=("$LOCAL_IP")
fi

if [ -n "$TAILSCALE_IP" ]; then
    echo -e "   2) Tailscale VPN: $TAILSCALE_IP"
    echo -e "      ${CYAN}→ Workers can connect from anywhere${NC}"
    OPTIONS+=("$TAILSCALE_IP")
fi

echo -e "   3) Custom IP (manual entry)"
echo ""

# Check if we have existing config
if [ -f "$INSTALL_DIR/config.env" ]; then
    source "$INSTALL_DIR/config.env"
    echo -e "   ${GREEN}Existing configuration found: $HEAD_IP${NC}"
    read -p "   Keep this configuration? (Y/n): " KEEP_CONFIG
    if [[ ! "$KEEP_CONFIG" =~ ^[Nn]$ ]]; then
        echo -e "   ✅ Using existing configuration"
    else
        HEAD_IP=""
    fi
fi

if [ -z "$HEAD_IP" ]; then
    read -p "   Your choice: " IP_CHOICE

    case $IP_CHOICE in
        1)
            if [ -n "$LOCAL_IP" ]; then
                HEAD_IP="$LOCAL_IP"
            else
                echo -e "${RED}   ❌ Local IP not available${NC}"
                exit 1
            fi
            ;;
        2)
            if [ -n "$TAILSCALE_IP" ]; then
                HEAD_IP="$TAILSCALE_IP"
            else
                echo -e "${RED}   ❌ Tailscale IP not available${NC}"
                exit 1
            fi
            ;;
        3)
            read -p "   Enter custom IP: " HEAD_IP
            if [ -z "$HEAD_IP" ]; then
                echo -e "${RED}   ❌ IP address required${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}   ❌ Invalid choice${NC}"
            exit 1
            ;;
    esac
fi

echo ""
echo -e "   ${GREEN}✅ Head Node will use: $HEAD_IP${NC}"

# ============================================================
# 5. INSTALL RAY AND DEPENDENCIES
# ============================================================
echo ""
echo -e "${YELLOW}[5/8]${NC} Installing Ray and dependencies..."

# Create directories
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/config"

# Check if pip exists for this Python
if ! "$PYTHON_CMD" -m pip --version &> /dev/null; then
    echo -e "   Installing pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | "$PYTHON_CMD"
fi

# Get pip path
PIP_CMD="$PYTHON_CMD -m pip"

echo -e "   Upgrading pip..."
$PIP_CMD install --upgrade pip setuptools wheel --quiet --user

echo -e "   Installing Ray 2.51.2..."
$PIP_CMD install --user "ray[default]==2.51.2" --quiet

echo -e "   Installing dependencies..."
$PIP_CMD install --user numpy pandas python-dotenv --quiet

# Verify installation
if "$PYTHON_CMD" -c "import ray; print(f'Ray {ray.__version__}')" &> /dev/null; then
    RAY_VERSION=$("$PYTHON_CMD" -c "import ray; print(ray.__version__)")
    echo -e "   ✅ Ray $RAY_VERSION installed successfully"
else
    echo -e "${RED}   ❌ Ray installation failed${NC}"
    exit 1
fi

# Get Ray binary path
RAY_PATH=$("$PYTHON_CMD" -c "import os, ray; print(os.path.join(os.path.dirname(ray.__file__), '../../../bin/ray'))" 2>/dev/null)
if [ ! -f "$RAY_PATH" ]; then
    # Fallback to user local bin
    RAY_PATH="$HOME/Library/Python/3.9/bin/ray"
fi

if [ ! -f "$RAY_PATH" ]; then
    echo -e "${RED}   ❌ Could not find Ray binary${NC}"
    exit 1
fi

echo -e "   ✅ Ray binary: $RAY_PATH"

# ============================================================
# 6. INSTALL HEAD DAEMON
# ============================================================
echo ""
echo -e "${YELLOW}[6/8]${NC} Installing Head Node daemon..."

# Copy daemon script
cp "$SCRIPT_DIR/head_daemon.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/head_daemon.sh"

# Update daemon with correct paths
sed -i.bak "s|/Users/enderj/Library/Python/3.9/bin/ray|$RAY_PATH|g" "$INSTALL_DIR/head_daemon.sh"
rm -f "$INSTALL_DIR/head_daemon.sh.bak"

# Save configuration
cat > "$INSTALL_DIR/config.env" << EOF
HEAD_IP=$HEAD_IP
LOCAL_IP=$LOCAL_IP
TAILSCALE_IP=$TAILSCALE_IP
NUM_CPUS=$NUM_CPUS
PYTHON_PATH=$PYTHON_CMD
RAY_PATH=$RAY_PATH
INSTALL_DATE=$(date)
VERSION=4.0
EOF

echo -e "   ✅ Daemon installed at: $INSTALL_DIR/head_daemon.sh"
echo -e "   ✅ Configuration saved: $INSTALL_DIR/config.env"

# ============================================================
# 7. CREATE LAUNCHD SERVICE (OPTIONAL)
# ============================================================
echo ""
echo -e "${YELLOW}[7/8]${NC} Configuring auto-start service..."

read -p "   Enable auto-start on login? (Y/n): " ENABLE_AUTOSTART

if [[ ! "$ENABLE_AUTOSTART" =~ ^[Nn]$ ]]; then
    LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_AGENTS_DIR"

    cat > "$LAUNCH_AGENTS_DIR/com.bittrader.head.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bittrader.head</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/head_daemon.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/logs/head.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/logs/head_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER</key>
        <string>1</string>
        <key>RAY_ENABLE_IPV6</key>
        <string>0</string>
    </dict>
</dict>
</plist>
EOF

    # Unload existing service
    launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.head.plist" 2>/dev/null || true

    # Load new service
    launchctl load "$LAUNCH_AGENTS_DIR/com.bittrader.head.plist"

    echo -e "   ✅ Auto-start enabled"

    AUTO_START_ENABLED=true
else
    echo -e "   ⊘ Auto-start disabled (can be enabled later)"
    AUTO_START_ENABLED=false
fi

# ============================================================
# 8. CONFIGURE FIREWALL (IF NEEDED)
# ============================================================
echo ""
echo -e "${YELLOW}[8/8]${NC} Checking firewall configuration..."

FIREWALL_ENABLED=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate | grep -q "enabled" && echo "true" || echo "false")

if [ "$FIREWALL_ENABLED" == "true" ]; then
    echo -e "${YELLOW}   ⚠️  Firewall is enabled${NC}"
    echo ""
    echo -e "   Ray Head Node requires incoming connections on port 6379."
    echo -e "   You may need to allow Python through the firewall."
    echo ""
    read -p "   Attempt to add firewall rule? (Y/n): " ADD_FIREWALL

    if [[ ! "$ADD_FIREWALL" =~ ^[Nn]$ ]]; then
        echo -e "   Adding firewall rule (requires administrator password)..."
        sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "$PYTHON_CMD" 2>/dev/null || true
        sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "$PYTHON_CMD" 2>/dev/null || true
        echo -e "   ✅ Firewall rule added"
    fi
else
    echo -e "   ✅ Firewall not enabled"
fi

# ============================================================
# INSTALLATION COMPLETE
# ============================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║              ✅ INSTALLATION COMPLETED SUCCESSFULLY          ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                  HEAD NODE CONFIGURATION                      ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   ${BLUE}Head Node IP:${NC}     $HEAD_IP"
echo -e "   ${BLUE}Port:${NC}             6379"
echo -e "   ${BLUE}CPUs Available:${NC}   $NUM_CPUS"
echo -e "   ${BLUE}Python Version:${NC}   $PYTHON_VERSION"
echo -e "   ${BLUE}Ray Version:${NC}      $RAY_VERSION"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    WORKER CONNECTION                          ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   Workers can connect using this command:"
echo ""
echo -e "   ${YELLOW}ray start --address=\"$HEAD_IP:6379\"${NC}"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                      NEXT STEPS                               ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
if [ "$AUTO_START_ENABLED" == "true" ]; then
    echo -e "   1. Head Node will start automatically on next login"
    echo -e "   2. To start now: $INSTALL_DIR/head_daemon.sh &"
else
    echo -e "   1. To start Head Node: $INSTALL_DIR/head_daemon.sh &"
fi
echo -e "   3. To verify status: ./verify_head.sh"
echo -e "   4. Install workers using the Worker Installer packages"
echo -e "   5. To uninstall: ./uninstall_head.sh"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                        LOGS                                   ${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "   Main log:   $INSTALL_DIR/logs/head.log"
echo -e "   Error log:  $INSTALL_DIR/logs/head_error.log"
echo ""
echo -e "${GREEN}Thank you for using Bittrader Ray Cluster!${NC}"
echo ""

# Start now?
read -p "Start Head Node now? (Y/n): " START_NOW

if [[ ! "$START_NOW" =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${BLUE}Starting Head Node...${NC}"

    # Start in background
    nohup "$INSTALL_DIR/head_daemon.sh" > /dev/null 2>&1 &

    echo -e "   Waiting for Head Node to initialize..."
    sleep 5

    # Verify
    if pgrep -f "ray.*head" > /dev/null; then
        echo -e "   ${GREEN}✅ Head Node is running!${NC}"
        echo ""
        echo -e "   Check status with: ./verify_head.sh"
    else
        echo -e "${YELLOW}   ⚠️  Head Node may still be starting...${NC}"
        echo -e "   Check logs: tail -f $INSTALL_DIR/logs/head.log"
    fi
    echo ""
fi

echo -e "${BLUE}Installation directory: $INSTALL_DIR${NC}"
echo ""
