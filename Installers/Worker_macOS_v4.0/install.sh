#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  BITTRADER WORKER v4.0 - macOS (AUTO-CONFIG)
#═══════════════════════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/crypto_worker"
VERSION="4.0"

# ══════════════════════════════════════════════════════════════════════════════
# COORDINATOR URL PRE-CONFIGURADA
# ══════════════════════════════════════════════════════════════════════════════
COORDINATOR_URL="http://100.77.179.14:5001"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║    BITTRADER WORKER v4.0 - macOS (AUTO-INSTALL)              ║"
echo "║                                                               ║"
echo "║    4000x speedup • Multi-worker • Auto-start                 ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}Coordinator: $COORDINATOR_URL${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Detect system
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[1/6]${NC} Detecting system..."
MACOS_VERSION=$(sw_vers -productVersion)
ARCH=$(uname -m)
echo -e "   ${GREEN}macOS $MACOS_VERSION ($ARCH)${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Check/Install Homebrew and Python
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[2/6]${NC} Checking dependencies..."

if ! command -v brew &> /dev/null; then
    echo -e "   Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

PYTHON_CMD=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "   Installing Python..."
    brew install python@3.12
    PYTHON_CMD="python3.12"
    version="3.12"
fi
echo -e "   ${GREEN}✓ Python $version${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Create venv
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[3/6]${NC} Creating environment..."

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

$PYTHON_CMD -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
pip install numba pandas requests numpy -q

echo -e "   ${GREEN}✓ Numba JIT installed (4000x speedup)${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Copy files
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[4/6]${NC} Installing files..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/crypto_worker.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/strategy_miner.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/numba_backtester.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/backtester.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/dynamic_strategy.py" "$INSTALL_DIR/"

mkdir -p "$INSTALL_DIR/data"
cp "$SCRIPT_DIR/data/BTC-USD_FIVE_MINUTE.csv" "$INSTALL_DIR/data/" 2>/dev/null || true

cat > "$INSTALL_DIR/config.env" << EOF
COORDINATOR_URL=$COORDINATOR_URL
VERSION=$VERSION
EOF

cat > "$INSTALL_DIR/config.py" << 'EOF'
class Config:
    TRADING_FEE_MAKER = 0.4
    TRADING_FEE_TAKER = 0.6
EOF

echo -e "   ${GREEN}✓ Files installed${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Configure workers
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[5/6]${NC} Configuring workers..."

CPU_COUNT=$(sysctl -n hw.ncpu)
if [ "$CPU_COUNT" -gt 16 ]; then NUM_WORKERS=6
elif [ "$CPU_COUNT" -gt 8 ]; then NUM_WORKERS=4
elif [ "$CPU_COUNT" -gt 4 ]; then NUM_WORKERS=3
else NUM_WORKERS=2; fi

echo -e "   ${GREEN}CPUs: $CPU_COUNT → $NUM_WORKERS workers${NC}"

# Start script with caffeinate (prevents sleep)
cat > "$INSTALL_DIR/start.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
export COORDINATOR_URL="$COORDINATOR_URL"

# Stop existing workers and caffeinate
pkill -f "crypto_worker.py" 2>/dev/null
pkill -f "caffeinate.*bittrader" 2>/dev/null
sleep 2

echo "Starting $NUM_WORKERS workers..."
echo "☕ Sleep prevention enabled (caffeinate)"

for i in \$(seq 1 $NUM_WORKERS); do
    WORKER_INSTANCE=\$i NUM_WORKERS=$NUM_WORKERS nohup ./venv/bin/python -u crypto_worker.py > /tmp/worker_\$i.log 2>&1 &
    sleep 2
done

# Keep system awake while workers run (caffeinate in background)
# -d: prevent display sleep, -i: prevent idle sleep, -m: prevent disk sleep, -s: prevent system sleep
nohup caffeinate -dims -w \$\$ > /dev/null 2>&1 &
echo \$! > "$INSTALL_DIR/.caffeinate.pid"

echo "Done! Logs: tail -f /tmp/worker_1.log"
echo "💡 System will stay awake while workers are running"
EOF
chmod +x "$INSTALL_DIR/start.sh"

cat > "$INSTALL_DIR/stop.sh" << EOF
#!/bin/bash
pkill -f "crypto_worker.py" 2>/dev/null
# Also stop caffeinate
if [ -f "$INSTALL_DIR/.caffeinate.pid" ]; then
    kill \$(cat "$INSTALL_DIR/.caffeinate.pid") 2>/dev/null
    rm "$INSTALL_DIR/.caffeinate.pid"
fi
pkill -f "caffeinate.*bittrader" 2>/dev/null
echo "Workers stopped"
echo "💤 Sleep prevention disabled"
EOF
chmod +x "$INSTALL_DIR/stop.sh"

cat > "$INSTALL_DIR/status.sh" << EOF
#!/bin/bash
echo "Workers: \$(ps aux | grep crypto_worker | grep -v grep | wc -l) running"
for i in \$(seq 1 $NUM_WORKERS); do
    echo "W\$i: \$(grep 'Gen [0-9].*PnL' /tmp/worker_\$i.log 2>/dev/null | tail -1 || echo 'No data')"
done
EOF
chmod +x "$INSTALL_DIR/status.sh"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 6: LaunchAgent for autostart
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[6/6]${NC} Setting up autostart..."

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$HOME/Library/LaunchAgents/com.bittrader.worker.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.bittrader.worker</string>
    <key>ProgramArguments</key><array><string>$INSTALL_DIR/start.sh</string></array>
    <key>RunAtLoad</key><true/>
    <key>EnvironmentVariables</key><dict>
        <key>PATH</key><string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

launchctl unload "$HOME/Library/LaunchAgents/com.bittrader.worker.plist" 2>/dev/null || true
launchctl load "$HOME/Library/LaunchAgents/com.bittrader.worker.plist"

echo -e "   ${GREEN}✓ Autostart enabled${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              INSTALLATION COMPLETE!                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   Workers: ${CYAN}$NUM_WORKERS${NC}"
echo -e "   Location: ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Starting workers...${NC}"
echo ""

cd "$INSTALL_DIR"
./start.sh
