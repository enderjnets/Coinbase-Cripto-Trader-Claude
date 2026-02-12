#!/bin/bash
#
# Bittrader Head Node Uninstaller v4.0
# Completely removes the Head Node installation
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

HEAD_DIR="$HOME/.bittrader_head"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║          Bittrader Head Node Uninstaller v4.0               ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${RED}This will completely remove the Head Node installation.${NC}"
echo ""
read -p "Are you sure? (y/N): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo "Uninstalling Head Node..."

# Stop and unload LaunchAgent
if [ -f "$LAUNCH_AGENTS_DIR/com.bittrader.head.plist" ]; then
    echo "  • Stopping auto-start service..."
    launchctl unload "$LAUNCH_AGENTS_DIR/com.bittrader.head.plist" 2>/dev/null || true
    rm -f "$LAUNCH_AGENTS_DIR/com.bittrader.head.plist"
fi

# Stop Ray
if [ -f "$HEAD_DIR/config.env" ]; then
    source "$HEAD_DIR/config.env"

    if [ -f "$RAY_PATH" ]; then
        echo "  • Stopping Ray Head..."
        "$RAY_PATH" stop 2>/dev/null || true
    fi
fi

# Kill daemon if running
if [ -f "$HEAD_DIR/head_daemon.lock" ]; then
    DAEMON_PID=$(cat "$HEAD_DIR/head_daemon.lock")
    if kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo "  • Stopping daemon (PID: $DAEMON_PID)..."
        kill "$DAEMON_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$DAEMON_PID" 2>/dev/null || true
    fi
fi

# Remove installation directory
if [ -d "$HEAD_DIR" ]; then
    echo "  • Removing installation directory..."
    rm -rf "$HEAD_DIR"
fi

echo ""
echo -e "${GREEN}✅ Head Node uninstalled successfully${NC}"
echo ""
echo "Note: Python and Ray packages were not removed."
echo "To remove them manually:"
echo "  pip3.9 uninstall ray"
echo ""
