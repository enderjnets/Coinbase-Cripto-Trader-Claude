#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════════
#  BITTRADER WORKER INSTALLER v4.0 - LINUX (AUTO-CONFIG)
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
echo "║    BITTRADER WORKER v4.0 - LINUX (AUTO-INSTALL)              ║"
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

if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "   ${GREEN}$NAME${NC}"
fi

if command -v apt-get &> /dev/null; then
    PKG_INSTALL="sudo apt-get install -y"
    sudo apt-get update -qq 2>/dev/null
elif command -v dnf &> /dev/null; then
    PKG_INSTALL="sudo dnf install -y"
elif command -v yum &> /dev/null; then
    PKG_INSTALL="sudo yum install -y"
elif command -v pacman &> /dev/null; then
    PKG_INSTALL="sudo pacman -S --noconfirm"
else
    echo -e "${RED}No supported package manager${NC}"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Install dependencies
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[2/6]${NC} Installing dependencies..."
$PKG_INSTALL python3 python3-venv python3-pip curl > /dev/null 2>&1 || true

# Install caffeine for sleep prevention (optional, won't fail if unavailable)
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y caffeine 2>/dev/null || true
fi
echo -e "   ${GREEN}✓ Done${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Find Python
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[3/6]${NC} Checking Python..."

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
    echo -e "${RED}Python 3.10+ required${NC}"
    exit 1
fi
echo -e "   ${GREEN}✓ $PYTHON_CMD ($version)${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Create venv and install packages
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[4/6]${NC} Creating environment..."

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

$PYTHON_CMD -m venv venv
source venv/bin/activate

pip install --upgrade pip -q
pip install numba pandas requests numpy -q

echo -e "   ${GREEN}✓ Numba JIT installed (4000x speedup)${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# Step 5: Copy files
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[5/6]${NC} Installing files..."

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
# Step 6: Create scripts and autostart
# ═══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}[6/6]${NC} Configuring..."

CPU_COUNT=$(nproc)
if [ "$CPU_COUNT" -gt 16 ]; then NUM_WORKERS=8
elif [ "$CPU_COUNT" -gt 8 ]; then NUM_WORKERS=5
elif [ "$CPU_COUNT" -gt 4 ]; then NUM_WORKERS=3
else NUM_WORKERS=2; fi

# Start script with sleep prevention
cat > "$INSTALL_DIR/start.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
export COORDINATOR_URL="$COORDINATOR_URL"

# Stop existing workers and sleep inhibitors
pkill -f "crypto_worker.py" 2>/dev/null
pkill -f "systemd-inhibit.*bittrader" 2>/dev/null
sleep 2

echo "Starting $NUM_WORKERS workers..."

for i in \$(seq 1 $NUM_WORKERS); do
    WORKER_INSTANCE=\$i NUM_WORKERS=$NUM_WORKERS nohup ./venv/bin/python -u crypto_worker.py > worker_\$i.log 2>&1 &
    sleep 2
done

# Prevent system sleep while workers are running
# Method 1: systemd-inhibit (most reliable on modern Linux)
if command -v systemd-inhibit &> /dev/null; then
    echo "☕ Sleep prevention enabled (systemd-inhibit)"
    nohup systemd-inhibit --what=idle:sleep:handle-lid-switch --who="Bittrader Worker" --why="Mining crypto strategies" --mode=block sleep infinity > /dev/null 2>&1 &
    echo \$! > "$INSTALL_DIR/.inhibit.pid"
# Method 2: Disable sleep via gsettings (GNOME/KDE)
elif command -v gsettings &> /dev/null; then
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' 2>/dev/null || true
    gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing' 2>/dev/null || true
    echo "☕ Sleep prevention enabled (gsettings)"
# Method 3: xset (X11)
elif command -v xset &> /dev/null; then
    xset s off -dpms 2>/dev/null || true
    echo "☕ Sleep prevention enabled (xset)"
fi

echo "Done! Logs: tail -f $INSTALL_DIR/worker_1.log"
echo "💡 System will stay awake while workers are running"
EOF
chmod +x "$INSTALL_DIR/start.sh"

# Stop script
cat > "$INSTALL_DIR/stop.sh" << EOF
#!/bin/bash
pkill -f "crypto_worker.py" 2>/dev/null

# Restore sleep settings
if [ -f "$INSTALL_DIR/.inhibit.pid" ]; then
    kill \$(cat "$INSTALL_DIR/.inhibit.pid") 2>/dev/null
    rm "$INSTALL_DIR/.inhibit.pid"
fi
pkill -f "systemd-inhibit.*bittrader" 2>/dev/null
pkill -f "systemd-inhibit.*Bittrader" 2>/dev/null

# Restore gsettings (optional - uncomment if needed)
# gsettings reset org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 2>/dev/null || true

echo "Workers stopped"
echo "💤 Sleep prevention disabled"
EOF
chmod +x "$INSTALL_DIR/stop.sh"

# Status script
cat > "$INSTALL_DIR/status.sh" << EOF
#!/bin/bash
echo "Workers: \$(ps aux | grep crypto_worker | grep -v grep | wc -l) running"
for i in \$(seq 1 $NUM_WORKERS); do
    echo "W\$i: \$(grep 'Gen [0-9].*PnL' $INSTALL_DIR/worker_\$i.log 2>/dev/null | tail -1 || echo 'No data')"
done
EOF
chmod +x "$INSTALL_DIR/status.sh"

# Autostart
cat > "$INSTALL_DIR/autostart.sh" << EOF
#!/bin/bash
sleep 30
cd "$INSTALL_DIR" && ./start.sh >> autostart.log 2>&1
EOF
chmod +x "$INSTALL_DIR/autostart.sh"

(crontab -l 2>/dev/null | grep -v "crypto_worker/autostart"; echo "@reboot $INSTALL_DIR/autostart.sh") | crontab -

echo -e "   ${GREEN}✓ $NUM_WORKERS workers configured${NC}"
echo -e "   ${GREEN}✓ Autostart enabled${NC}"

# ═══════════════════════════════════════════════════════════════════════════════
# DONE - Auto start workers
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              INSTALLATION COMPLETE!                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   Workers: ${CYAN}$NUM_WORKERS${NC}"
echo -e "   Location: ${CYAN}$INSTALL_DIR${NC}"
echo ""
echo -e "${YELLOW}Starting workers automatically...${NC}"
echo ""

cd "$INSTALL_DIR"
./start.sh
