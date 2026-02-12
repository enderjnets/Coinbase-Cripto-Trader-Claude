#!/bin/bash
#
# Bittrader Head Node Daemon v4.0
# Persistent Ray Head Node daemon with automatic restart
# Optimized for production deployment
#

set -e

HEAD_DIR="$HOME/.bittrader_head"
LOG_FILE="$HEAD_DIR/logs/head.log"
LOCK_FILE="$HEAD_DIR/head_daemon.lock"

# Create directories
mkdir -p "$HEAD_DIR/logs"

# Check if already running
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Head daemon already running (PID: $PID)"
        exit 1
    fi
fi

# Create lock file
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# Load configuration
if [ -f "$HEAD_DIR/config.env" ]; then
    source "$HEAD_DIR/config.env"
else
    echo "ERROR: Configuration file not found: $HEAD_DIR/config.env"
    exit 1
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Detect Tailscale IP dynamically (in case it changes)
detect_tailscale_ip() {
    if command -v tailscale &> /dev/null; then
        tailscale ip -4 2>/dev/null || echo ""
    elif [ -f "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]; then
        /Applications/Tailscale.app/Contents/MacOS/Tailscale ip -4 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Update HEAD_IP if using Tailscale and IP changed
if [[ "$HEAD_IP" == 100.* ]]; then
    CURRENT_TS_IP=$(detect_tailscale_ip)
    if [ -n "$CURRENT_TS_IP" ] && [ "$CURRENT_TS_IP" != "$HEAD_IP" ]; then
        log "Tailscale IP changed from $HEAD_IP to $CURRENT_TS_IP"
        HEAD_IP="$CURRENT_TS_IP"
        # Update config file
        sed -i.bak "s/HEAD_IP=.*/HEAD_IP=$HEAD_IP/" "$HEAD_DIR/config.env"
        rm -f "$HEAD_DIR/config.env.bak"
    fi
fi

log "╔════════════════════════════════════════════════════════════╗"
log "║    Head Node Daemon v4.0 Starting                         ║"
log "╚════════════════════════════════════════════════════════════╝"
log ""
log "Configuration:"
log "  • Head IP: $HEAD_IP"
log "  • Port: 6379"
log "  • CPUs: $NUM_CPUS"
log "  • Python: $PYTHON_PATH"
log "  • Ray: $RAY_PATH"
log ""

# Enable cluster mode
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
export RAY_ENABLE_IPV6=0

# Main loop with automatic restart
RESTART_COUNT=0
MAX_RESTARTS=999999

while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    # Stop any existing Ray instance
    "$RAY_PATH" stop &>/dev/null || true
    sleep 2

    log "Starting Ray Head Node (attempt $((RESTART_COUNT + 1)))..."
    log "  ray start --head --port=6379 --node-ip-address=$HEAD_IP --num-cpus=$NUM_CPUS"

    # Start Ray Head
    "$RAY_PATH" start --head \
        --port=6379 \
        --node-ip-address="$HEAD_IP" \
        --include-dashboard=false \
        --num-cpus="$NUM_CPUS" \
        --block >> "$LOG_FILE" 2>&1 &

    RAY_PID=$!
    log "✅ Ray Head started with PID $RAY_PID"

    # Monitor Ray process
    while kill -0 "$RAY_PID" 2>/dev/null; do
        sleep 30

        # Periodic health check
        if ! "$PYTHON_PATH" -c "import ray; ray.init(address='auto', ignore_reinit_error=True); print(ray.cluster_resources())" &>/dev/null; then
            log "⚠️  Health check failed, Ray may be unhealthy"
            kill "$RAY_PID" 2>/dev/null || true
            break
        fi
    done

    RESTART_COUNT=$((RESTART_COUNT + 1))
    log "❌ Ray process died unexpectedly"
    log "   Restarting in 15 seconds (restart #$RESTART_COUNT)..."
    sleep 15
done

log "❌ Maximum restart attempts reached. Exiting."
