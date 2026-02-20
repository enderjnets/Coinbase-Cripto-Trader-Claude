# 0. Get the ABSOLUTE directory where the script is located
# This handles being called from Desktop shortcuts or other folders
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Environment Config
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
export RAY_ENABLE_IPV6=0
export RAY_IGNORE_VERSION_MISMATCH=1
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
VENV_RAY="$SCRIPT_DIR/.venv/bin/ray"

# 2. Smart IP Detection (Prefer Tailscale for remote workers)
LAN_IP=$(ipconfig getifaddr en0)
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")

if [ ! -z "$TAILSCALE_IP" ]; then
    HEAD_IP=$TAILSCALE_IP
    echo -e "${GREEN}Tailscale detected: $TAILSCALE_IP${NC}"
else
    HEAD_IP=$LAN_IP
    echo -e "Using LAN IP: $LAN_IP"
fi

# 3. Stop old instances cleanly
echo "🧹 Cleaning up old processes..."
$VENV_RAY stop --force &> /dev/null
pkill -f streamlit &> /dev/null
pkill -f beacon.py &> /dev/null

# 4. Start Ray Head
# Use the detected HEAD_IP (Tailscale if available) as the node identity
echo "🚀 Starting Ray Head Node on $HEAD_IP..."
$VENV_RAY start --head --port=6379 \
    --node-ip-address=$HEAD_IP \
    --dashboard-host=0.0.0.0 \
    --include-dashboard=true \
    --disable-usage-stats

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Ray Head STARTED SUCCESSFULLY!${NC}"
    
    # 5. Start Auto-Discovery Beacon
    echo "📡 Starting Auto-Discovery Beacon..."
    $VENV_PYTHON beacon.py > /dev/null 2>&1 &
    
    echo ""
    echo "-------------------------------------------------------"
    echo "HEAD NODE IP: $HEAD_IP"
    echo "Worker setup: ./setup_worker.sh"
    echo "-------------------------------------------------------"
    echo ""
    
    # 6. Launch Streamlit UI
    echo "🎨 Launching Streamlit Interface..."
    # Launch in foreground so the terminal stays open and logs are visible
    $VENV_PYTHON -m streamlit run interface.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=false
else
    echo -e "\033[0;31m❌ ERROR: Failed to start Ray Head Node.\033[0m"
    exit 1
fi
