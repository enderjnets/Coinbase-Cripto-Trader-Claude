#!/bin/bash
#
# Bittrader Worker Uninstaller - Linux Edition
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.bittrader_worker"

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║        Bittrader Worker Uninstaller (Linux)                 ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${RED}This will completely remove the Bittrader Worker.${NC}"
echo ""
read -p "Are you sure? (y/N): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo "Uninstalling..."

# Stop and disable systemd service
if systemctl --user list-units --full --all | grep -q "bittrader-worker"; then
    echo "  • Stopping systemd service..."
    sudo systemctl stop bittrader-worker 2>/dev/null || true
    sudo systemctl disable bittrader-worker 2>/dev/null || true
    sudo rm -f /etc/systemd/system/bittrader-worker.service
    sudo systemctl daemon-reload
fi

# Stop Ray
if [ -f "$INSTALL_DIR/venv/bin/ray" ]; then
    echo "  • Stopping Ray..."
    "$INSTALL_DIR/venv/bin/ray" stop 2>/dev/null || true
fi

# Kill daemon if running
if [ -f "$INSTALL_DIR/worker_daemon.lock" ]; then
    DAEMON_PID=$(cat "$INSTALL_DIR/worker_daemon.lock")
    if kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo "  • Stopping daemon (PID: $DAEMON_PID)..."
        kill "$DAEMON_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$DAEMON_PID" 2>/dev/null || true
    fi
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    echo "  • Removing installation directory..."
    rm -rf "$INSTALL_DIR"
fi

echo ""
echo -e "${GREEN}✅ Worker uninstalled successfully${NC}"
echo ""
echo "Note: Python and system packages were not removed."
echo ""
