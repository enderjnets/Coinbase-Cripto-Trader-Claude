#!/bin/bash
#
# Bittrader Head Node Verification Script v4.0
# Verifies that the Head Node is running and healthy
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

HEAD_DIR="$HOME/.bittrader_head"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        Bittrader Head Node Status Verification v4.0         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if config exists
if [ ! -f "$HEAD_DIR/config.env" ]; then
    echo -e "${RED}❌ Head Node not installed${NC}"
    echo "   Run ./setup_head_native.sh to install"
    exit 1
fi

# Load config
source "$HEAD_DIR/config.env"

echo -e "${BLUE}Configuration:${NC}"
echo -e "   Head IP:        $HEAD_IP"
echo -e "   Port:           6379"
echo -e "   CPUs:           $NUM_CPUS"
echo -e "   Version:        $VERSION"
echo -e "   Installed:      $INSTALL_DATE"
echo ""

# Check if daemon is running
echo -e "${BLUE}Daemon Status:${NC}"

if [ -f "$HEAD_DIR/head_daemon.lock" ]; then
    DAEMON_PID=$(cat "$HEAD_DIR/head_daemon.lock")
    if kill -0 "$DAEMON_PID" 2>/dev/null; then
        echo -e "   ${GREEN}✅ Daemon running (PID: $DAEMON_PID)${NC}"
    else
        echo -e "   ${RED}❌ Daemon not running (stale lock file)${NC}"
        rm -f "$HEAD_DIR/head_daemon.lock"
    fi
else
    echo -e "   ${RED}❌ Daemon not running${NC}"
fi

# Check if Ray is running
echo ""
echo -e "${BLUE}Ray Status:${NC}"

if pgrep -f "ray.*head" > /dev/null; then
    echo -e "   ${GREEN}✅ Ray Head process running${NC}"

    # Get Ray PID
    RAY_PID=$(pgrep -f "ray.*head" | head -1)
    echo -e "   PID: $RAY_PID"

    # Check Ray health
    if [ -f "$PYTHON_PATH" ]; then
        echo ""
        echo -e "${BLUE}Cluster Resources:${NC}"

        RESOURCES=$("$PYTHON_PATH" -c "
import ray
try:
    ray.init(address='auto', ignore_reinit_error=True)
    resources = ray.cluster_resources()
    print(f\"   CPUs: {resources.get('CPU', 0)}\")
    print(f\"   Memory: {resources.get('memory', 0) / 1e9:.2f} GB\")
    print(f\"   Nodes: {len(ray.nodes())}\")
    ray.shutdown()
except Exception as e:
    print(f\"   Error: {e}\")
" 2>&1)

        if echo "$RESOURCES" | grep -q "Error"; then
            echo -e "   ${YELLOW}⚠️  Could not connect to Ray cluster${NC}"
            echo "$RESOURCES"
        else
            echo "$RESOURCES"
        fi
    fi
else
    echo -e "   ${RED}❌ Ray Head not running${NC}"
fi

# Check network connectivity
echo ""
echo -e "${BLUE}Network Connectivity:${NC}"

if ping -c 1 -W 2 "$HEAD_IP" &> /dev/null; then
    echo -e "   ${GREEN}✅ Head IP reachable: $HEAD_IP${NC}"
else
    echo -e "   ${RED}❌ Head IP not reachable: $HEAD_IP${NC}"
fi

# Check port 6379
if command -v nc &> /dev/null; then
    if nc -z -w 2 "$HEAD_IP" 6379 2>/dev/null; then
        echo -e "   ${GREEN}✅ Port 6379 open${NC}"
    else
        echo -e "   ${RED}❌ Port 6379 not accessible${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠️  netcat not available (cannot check port)${NC}"
fi

# Show worker connection command
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                 Worker Connection Command                    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   Workers can connect with:"
echo ""
echo -e "   ${YELLOW}ray start --address=\"$HEAD_IP:6379\"${NC}"
echo ""

# Show recent logs
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                      Recent Logs                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ -f "$HEAD_DIR/logs/head.log" ]; then
    echo -e "${BLUE}Last 10 lines from head.log:${NC}"
    echo ""
    tail -10 "$HEAD_DIR/logs/head.log"
else
    echo -e "${YELLOW}   No logs found${NC}"
fi

echo ""
echo -e "${BLUE}For continuous monitoring:${NC}"
echo -e "   tail -f $HEAD_DIR/logs/head.log"
echo ""
